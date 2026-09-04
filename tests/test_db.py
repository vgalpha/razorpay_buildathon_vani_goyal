"""Persistence tests against SQLite (portable, no external service needed --
see docs/STATUS.md for why the automated suite uses this while production
targets real Postgres/Neon). Each test opens a fresh engine against the same
on-disk file to simulate what a real process restart looks like -- not just
reads within one open connection.
"""

import os
import tempfile
import unittest

from reconciler import db, serialize
from reconciler.engine import reconcile
from reconciler.evaluate import evaluate
from reconciler.generate import generate_dataset


class TestBatchPersistence(unittest.TestCase):
  def setUp(self):
    fd, self.db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(self.db_path)  # let create_engine make a fresh file
    self.url = f"sqlite:///{self.db_path}"

  def tearDown(self):
    if os.path.exists(self.db_path):
      os.remove(self.db_path)

  def test_batch_round_trips_through_a_fresh_connection(self):
    dataset = generate_dataset(seed=1)
    engine1 = db.make_engine(self.url)
    db.insert_batch(engine1, "b1", 1, "synthetic", serialize.dataset_to_dict(dataset))

    engine2 = db.make_engine(self.url)  # simulates a new process after restart
    stored = db.fetch_batch(engine2, "b1")
    self.assertIsNotNone(stored)
    self.assertEqual(stored["seed"], 1)
    self.assertIsNone(stored["run_result"])
    restored = serialize.dataset_from_dict(stored["dataset"])
    self.assertEqual(len(restored.payments), len(dataset.payments))
    self.assertEqual(restored.payments[0], dataset.payments[0])

  def test_run_result_attaches_and_survives_a_fresh_connection(self):
    dataset = generate_dataset(seed=1)
    engine1 = db.make_engine(self.url)
    db.insert_batch(engine1, "b2", 1, "synthetic", serialize.dataset_to_dict(dataset))
    run = reconcile(dataset.payments, dataset.settlement_lines, dataset.invoices)
    ev = evaluate(run, dataset.ground_truth)
    db.set_run_result(engine1, "b2", serialize.run_to_dict(run, ev))

    engine2 = db.make_engine(self.url)
    stored = db.fetch_batch(engine2, "b2")
    self.assertIsNotNone(stored["run_result"])
    restored_run, restored_ev = serialize.run_from_dict(stored["run_result"])
    self.assertEqual(len(restored_run.decisions), len(run.decisions))
    self.assertEqual(restored_ev.overall_accuracy, ev.overall_accuracy)

  def test_unknown_batch_returns_none(self):
    engine = db.make_engine(self.url)
    self.assertIsNone(db.fetch_batch(engine, "does-not-exist"))

  def test_list_batches_only_includes_completed_runs(self):
    dataset = generate_dataset(seed=1)
    engine = db.make_engine(self.url)
    db.insert_batch(engine, "not-run-yet", 1, "synthetic", serialize.dataset_to_dict(dataset))
    db.insert_batch(engine, "completed", 2, "synthetic", serialize.dataset_to_dict(dataset))
    run = reconcile(dataset.payments, dataset.settlement_lines, dataset.invoices)
    ev = evaluate(run, dataset.ground_truth)
    db.set_run_result(engine, "completed", serialize.run_to_dict(run, ev))

    listed = db.list_batches(engine)
    self.assertEqual([b["id"] for b in listed], ["completed"])
    self.assertEqual(listed[0]["cases"], len(dataset.ground_truth))
    self.assertEqual(listed[0]["accuracy"], ev.overall_accuracy)
    self.assertTrue(listed[0]["created_at"].endswith("+00:00"))

  def test_ensure_summary_columns_is_idempotent_on_existing_table(self):
    engine = db.make_engine(self.url)
    db.make_engine(self.url)  # second call against the same already-migrated db
    dataset = generate_dataset(seed=1)
    db.insert_batch(engine, "b3", 1, "synthetic", serialize.dataset_to_dict(dataset))
    self.assertIsNotNone(db.fetch_batch(engine, "b3"))


if __name__ == "__main__":
  unittest.main()
