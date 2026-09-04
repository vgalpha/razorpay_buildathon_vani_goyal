"""Dataclass <-> plain-dict conversion for everything that needs to survive
a round trip through JSON (database storage, API payloads). One place for
this so api.py and db.py don't each invent their own dict-poking.
"""

import dataclasses

from reconciler.engine import Decision, ReconciliationRun
from reconciler.evaluate import EvalReport
from reconciler.generate import Dataset
from reconciler.schema import GroundTruthCase, Invoice, Payment, SettlementLine


def dataset_to_dict(dataset: Dataset) -> dict:
  return {
    "payments": [dataclasses.asdict(p) for p in dataset.payments],
    "settlement_lines": [dataclasses.asdict(s) for s in dataset.settlement_lines],
    "invoices": [dataclasses.asdict(i) for i in dataset.invoices],
    "ground_truth": [dataclasses.asdict(g) for g in dataset.ground_truth],
  }


def dataset_from_dict(d: dict) -> Dataset:
  return Dataset(
    payments=[Payment(**p) for p in d["payments"]],
    settlement_lines=[SettlementLine(**s) for s in d["settlement_lines"]],
    invoices=[Invoice(**i) for i in d["invoices"]],
    ground_truth=[GroundTruthCase(**g) for g in d["ground_truth"]],
  )


def run_to_dict(run: ReconciliationRun, ev: EvalReport) -> dict:
  return {
    "run": {
      "decisions": [dataclasses.asdict(d) for d in run.decisions],
      "pass_counts": run.pass_counts,
      "pass_timings_ms": run.pass_timings_ms,
      "pass_hit_counts": run.pass_hit_counts,
      "invariants": run.invariants,
      "wall_time_seconds": run.wall_time_seconds,
    },
    "eval": dataclasses.asdict(ev),
  }


def run_from_dict(d: dict):
  run_d = d["run"]
  run = ReconciliationRun(
    decisions=[Decision(**dd) for dd in run_d["decisions"]],
    pass_counts=run_d["pass_counts"],
    pass_timings_ms=run_d["pass_timings_ms"],
    pass_hit_counts=run_d["pass_hit_counts"],
    invariants=run_d["invariants"],
    wall_time_seconds=run_d["wall_time_seconds"],
  )
  ev = EvalReport(**d["eval"])
  return run, ev
