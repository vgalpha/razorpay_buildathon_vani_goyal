"""Real, persistent batch storage. Replaces the in-memory dict that used to
live in api.py -- the user asked for a genuine database, not a workaround.

Reads DATABASE_URL from the environment; works against any SQLAlchemy-
supported backend (Postgres in production -- Neon recommended, see
docs/STATUS.md -- SQLite for the automated test suite, which needs no
external service). No provider-specific behavior is hard-coded here.
"""

import json
import os
from datetime import datetime, timezone

from sqlalchemy import (
  Column, DateTime, Float, Integer, MetaData, String, Table, Text,
  create_engine, select, text,
)

metadata = MetaData()

batches = Table(
  "batches", metadata,
  Column("id", String, primary_key=True),
  Column("seed", Integer, nullable=False),
  Column("order_mode", String, nullable=False),
  Column("created_at", DateTime, nullable=False),
  Column("dataset_json", Text, nullable=False),
  Column("run_result_json", Text, nullable=True),
  # Summary columns, kept in sync with dataset_json/run_result_json, so the
  # history list can render without pulling every batch's full blob over
  # the wire. Nullable because rows written before these existed (and a
  # not-yet-run batch's accuracy/false_auto_close_rate) won't have them.
  Column("payments_count", Integer, nullable=True),
  Column("settlement_lines_count", Integer, nullable=True),
  Column("invoices_count", Integer, nullable=True),
  Column("cases_count", Integer, nullable=True),
  Column("accuracy", Float, nullable=True),
  Column("false_auto_close_rate", Float, nullable=True),
)

# (column, SQL type) for the summary columns above -- added via guarded ALTER
# so an already-deployed table (production Neon, or a pre-existing local
# reconciler.db) picks them up without a real migration tool. Each runs in
# its own transaction so "column already exists" on one doesn't abort the
# rest.
_SUMMARY_COLUMNS = [
  ("payments_count", "INTEGER"),
  ("settlement_lines_count", "INTEGER"),
  ("invoices_count", "INTEGER"),
  ("cases_count", "INTEGER"),
  ("accuracy", "DOUBLE PRECISION"),
  ("false_auto_close_rate", "DOUBLE PRECISION"),
]


def _ensure_summary_columns(engine):
  for name, sql_type in _SUMMARY_COLUMNS:
    try:
      with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE batches ADD COLUMN {name} {sql_type}"))
    except Exception:
      pass  # column already exists


def _backfill_summary_columns(engine):
  """Rows written before the summary columns existed have cases_count=NULL.
  Compute their summaries once from the blobs already on hand; after this,
  cases_count is set and the row is never re-selected here again -- so this
  stays cheap on every cold start after the first, and list_batches never
  needs to touch dataset_json/run_result_json itself.
  """
  with engine.begin() as conn:
    rows = conn.execute(
      select(batches.c.id, batches.c.dataset_json, batches.c.run_result_json)
      .where(batches.c.cases_count.is_(None))
    ).mappings().all()
    for r in rows:
      dataset = json.loads(r["dataset_json"])
      values = {
        "payments_count": len(dataset["payments"]),
        "settlement_lines_count": len(dataset["settlement_lines"]),
        "invoices_count": len(dataset["invoices"]),
        "cases_count": len(dataset["ground_truth"]),
      }
      if r["run_result_json"]:
        ev = json.loads(r["run_result_json"])["eval"]
        values["accuracy"] = ev["overall_accuracy"]
        values["false_auto_close_rate"] = ev["false_auto_close_rate"]
      conn.execute(batches.update().where(batches.c.id == r["id"]).values(**values))


def make_engine(database_url=None):
  url = database_url or os.environ.get("DATABASE_URL", "sqlite:///reconciler.db")
  engine = create_engine(url, future=True)
  metadata.create_all(engine)
  _ensure_summary_columns(engine)
  _backfill_summary_columns(engine)
  return engine


def insert_batch(engine, batch_id, seed, order_mode, dataset_dict):
  with engine.begin() as conn:
    conn.execute(batches.insert().values(
      id=batch_id, seed=seed, order_mode=order_mode,
      created_at=datetime.now(timezone.utc),
      dataset_json=json.dumps(dataset_dict), run_result_json=None,
      payments_count=len(dataset_dict["payments"]),
      settlement_lines_count=len(dataset_dict["settlement_lines"]),
      invoices_count=len(dataset_dict["invoices"]),
      cases_count=len(dataset_dict["ground_truth"]),
    ))


def set_run_result(engine, batch_id, run_result_dict):
  ev = run_result_dict["eval"]
  with engine.begin() as conn:
    conn.execute(
      batches.update().where(batches.c.id == batch_id)
      .values(
        run_result_json=json.dumps(run_result_dict),
        accuracy=ev["overall_accuracy"],
        false_auto_close_rate=ev["false_auto_close_rate"],
      ))


def fetch_batch(engine, batch_id):
  with engine.connect() as conn:
    row = conn.execute(
      select(batches).where(batches.c.id == batch_id)).mappings().first()
  if row is None:
    return None
  return {
    "seed": row["seed"],
    "order_mode": row["order_mode"],
    "dataset": json.loads(row["dataset_json"]),
    "run_result": json.loads(row["run_result_json"]) if row["run_result_json"] else None,
  }


def _as_utc_iso(dt):
  # Postgres/SQLite both return a naive datetime here even though the value
  # stored was UTC -- attach the offset explicitly so the frontend doesn't
  # parse it as local time (that would put every history row ~5:30 in the
  # past for an IST viewer).
  if dt.tzinfo is None:
    dt = dt.replace(tzinfo=timezone.utc)
  return dt.isoformat()


def list_batches(engine, limit=50):
  """Completed runs only, newest first, summary columns only -- no dataset
  or run_result blobs. "History" means runs a user can look back at, not
  half-created batches from an abandoned session.
  """
  cols = [
    batches.c.id, batches.c.created_at,
    batches.c.payments_count, batches.c.settlement_lines_count,
    batches.c.invoices_count, batches.c.cases_count,
    batches.c.accuracy, batches.c.false_auto_close_rate,
  ]
  with engine.connect() as conn:
    rows = conn.execute(
      select(*cols)
      .where(batches.c.run_result_json.isnot(None))
      .order_by(batches.c.created_at.desc())
      .limit(limit)
    ).mappings().all()
  return [
    {
      "id": r["id"],
      "created_at": _as_utc_iso(r["created_at"]),
      "payments": r["payments_count"],
      "settlement_lines": r["settlement_lines_count"],
      "invoices": r["invoices_count"],
      "cases": r["cases_count"],
      "accuracy": r["accuracy"],
      "false_auto_close_rate": r["false_auto_close_rate"],
    }
    for r in rows
  ]
