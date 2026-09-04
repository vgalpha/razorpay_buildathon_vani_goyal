"""Thin FastAPI wrapper around the reconciliation engine.

Batches persist in a real database (see reconciler/db.py) -- Postgres in
production (Neon recommended, see docs/STATUS.md), SQLite for tests. This
layer only ever calls into reconciler.* -- it must never reimplement
matching, scoring, or question-answering logic itself.
"""

import os
import time
import uuid
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from reconciler import db
from reconciler import qa as qa_module
from reconciler import serialize
from reconciler.engine import reconcile
from reconciler.evaluate import evaluate
from reconciler.generate import generate_dataset, jitter_taxonomy_counts, scale_taxonomy_counts
from reconciler.taxonomy import TAXONOMY

app = FastAPI(title="Reconciliation Engine API")
app.add_middleware(
  CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_ENGINE = db.make_engine()

# CORS is open and this endpoint is unauthenticated, so without this gate any
# caller could force the server to spend the account's real Razorpay
# credentials on live order creation. Off by default; set ALLOW_LIVE_ORDERS=1
# deliberately (e.g. for a local demo) to enable order_mode="live".
_ALLOW_LIVE_ORDERS = os.environ.get("ALLOW_LIVE_ORDERS") == "1"


TOTAL_CASES_MIN = 20
# Payload-size guardrail, not a compute-time one. Verified against the
# actual deployed function at this ceiling (2026-09-04): run ~1.6s at 100%
# accuracy, /data response ~660KB -- see docs/STATUS.md.
TOTAL_CASES_MAX = 1000


class GenerateRequest(BaseModel):
  seed: Optional[int] = None
  order_mode: str = "synthetic"
  # Both optional and independent of each other. Neither given: counts are
  # jittered for natural variety on every click (see resolve_fault_counts).
  # total_cases alone: every class scaled proportionally, no jitter -- a
  # user asking for a specific size wants predictable sizing, not more
  # variety on top. fault_counts alone or combined with total_cases:
  # explicit per-class values win over whatever total_cases would have
  # scaled them to.
  fault_counts: Optional[Dict[str, int]] = None
  total_cases: Optional[int] = None


class AskRequest(BaseModel):
  question: str


def _dataset_summary(dataset):
  return {
    "payments": len(dataset.payments),
    "settlement_lines": len(dataset.settlement_lines),
    "invoices": len(dataset.invoices),
    "cases": len(dataset.ground_truth),
  }


def _get_batch(batch_id):
  batch = db.fetch_batch(_ENGINE, batch_id)
  if batch is None:
    raise HTTPException(status_code=404, detail=f"unknown batch_id {batch_id}")
  return batch


def _run_payload(run, ev):
  return {
    "decisions": [d.__dict__ for d in run.decisions],
    "pass_counts": run.pass_counts,
    "pass_timings_ms": run.pass_timings_ms,
    "pass_hit_counts": run.pass_hit_counts,
    "invariants": run.invariants,
    "wall_time_seconds": run.wall_time_seconds,
    "eval": {
      "total_cases": ev.total_cases,
      "overall_accuracy": ev.overall_accuracy,
      "false_auto_close_rate": ev.false_auto_close_rate,
      "auto_close_precision": ev.auto_close_precision,
      "auto_close_recall": ev.auto_close_recall,
      "auto_close_f1": ev.auto_close_f1,
      "throughput_per_sec": ev.throughput_per_sec,
      "per_fault_class": ev.per_fault_class,
      "per_rule": ev.per_rule,
    },
  }


def _resolve_fault_counts(req, seed):
  """Turns a request's (fault_counts, total_cases) into the single resolved
  {fault_type: count} dict generate_dataset actually needs -- generate_dataset
  itself stays pure/deterministic-given-its-args (see its docstring), so all
  of this "how do we decide the sizes" policy lives here instead."""
  if req.fault_counts is not None:
    unknown = set(req.fault_counts) - set(TAXONOMY)
    if unknown:
      raise HTTPException(
        status_code=400, detail=f"unknown fault type(s): {sorted(unknown)}")
    base = scale_taxonomy_counts(_clamp_total_cases(req.total_cases)) \
      if req.total_cases is not None else {ft: spec.count for ft, spec in TAXONOMY.items()}
    return {**base, **{ft: max(0, int(n)) for ft, n in req.fault_counts.items()}}
  if req.total_cases is not None:
    return scale_taxonomy_counts(_clamp_total_cases(req.total_cases))
  return jitter_taxonomy_counts(seed)


def _clamp_total_cases(total_cases):
  return max(TOTAL_CASES_MIN, min(TOTAL_CASES_MAX, total_cases))


@app.post("/batches")
def create_batch(req: GenerateRequest):
  if req.order_mode == "live" and not _ALLOW_LIVE_ORDERS:
    raise HTTPException(
      status_code=403,
      detail="order_mode='live' is disabled on this deployment "
             "(set ALLOW_LIVE_ORDERS=1 to enable it deliberately)")
  seed = req.seed if req.seed is not None else int(time.time() * 1000) % 100_000
  fault_counts = _resolve_fault_counts(req, seed)
  dataset = generate_dataset(seed=seed, order_mode=req.order_mode, fault_counts=fault_counts)
  batch_id = uuid.uuid4().hex[:12]
  db.insert_batch(
    _ENGINE, batch_id, seed, req.order_mode, serialize.dataset_to_dict(dataset))
  return {"batch_id": batch_id, "seed": seed, **_dataset_summary(dataset)}


@app.get("/taxonomy")
def get_taxonomy():
  """The fault-type catalog, for the frontend's optional "customize this
  batch" panel -- single source of truth stays taxonomy.py, this just
  reflects it instead of duplicating the list client-side."""
  return {
    "fault_types": [
      {
        "fault_type": ft,
        "description": spec.description,
        "default_count": spec.count,
        "expected_decision": spec.expected_decision,
      }
      for ft, spec in TAXONOMY.items()
    ]
  }


@app.post("/batches/{batch_id}/run")
def run_batch(batch_id: str):
  batch = _get_batch(batch_id)
  dataset = serialize.dataset_from_dict(batch["dataset"])
  run = reconcile(dataset.payments, dataset.settlement_lines, dataset.invoices)
  ev = evaluate(run, dataset.ground_truth)
  db.set_run_result(_ENGINE, batch_id, serialize.run_to_dict(run, ev))
  return _run_payload(run, ev)


@app.get("/batches/{batch_id}")
def get_batch(batch_id: str):
  batch = _get_batch(batch_id)
  if batch["run_result"] is None:
    raise HTTPException(status_code=404, detail="batch generated but not yet run")
  run, ev = serialize.run_from_dict(batch["run_result"])
  return _run_payload(run, ev)


@app.get("/batches/{batch_id}/data")
def get_batch_data(batch_id: str):
  """The raw records a batch was generated from, for a "what are we working
  with" preview/download. Deliberately excludes ground_truth -- that's the
  answer key, and showing it next to the data invites the wrong question
  from anyone evaluating the reconciliation accuracy.
  """
  batch = _get_batch(batch_id)
  dataset = batch["dataset"]
  return {
    "payments": dataset["payments"],
    "settlement_lines": dataset["settlement_lines"],
    "invoices": dataset["invoices"],
  }


@app.get("/batches")
def list_batches():
  return {"batches": db.list_batches(_ENGINE)}


@app.post("/batches/{batch_id}/ask")
def ask_batch(batch_id: str, req: AskRequest):
  batch = _get_batch(batch_id)
  if batch["run_result"] is None:
    raise HTTPException(status_code=400, detail="run the batch before asking questions")
  run, ev = serialize.run_from_dict(batch["run_result"])
  dataset = serialize.dataset_from_dict(batch["dataset"])
  answer = qa_module.answer(req.question, run, ev, dataset.payments)
  return {"question": req.question, "answer": answer}
