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
  Column, DateTime, Integer, MetaData, String, Table, Text, create_engine,
  select,
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
)


def make_engine(database_url=None):
  url = database_url or os.environ.get("DATABASE_URL", "sqlite:///reconciler.db")
  engine = create_engine(url, future=True)
  metadata.create_all(engine)
  return engine


def insert_batch(engine, batch_id, seed, order_mode, dataset_dict):
  with engine.begin() as conn:
    conn.execute(batches.insert().values(
      id=batch_id, seed=seed, order_mode=order_mode,
      created_at=datetime.now(timezone.utc),
      dataset_json=json.dumps(dataset_dict), run_result_json=None,
    ))


def set_run_result(engine, batch_id, run_result_dict):
  with engine.begin() as conn:
    conn.execute(
      batches.update().where(batches.c.id == batch_id)
      .values(run_result_json=json.dumps(run_result_dict)))


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
