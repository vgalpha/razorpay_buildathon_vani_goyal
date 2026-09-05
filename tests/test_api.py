"""Endpoint-level tests for reconciler/api.py, run through FastAPI's real
request/response cycle (TestClient) rather than calling handler functions
directly, so behavior like 404s is actually exercised end to end.

DATABASE_URL must point at a throwaway SQLite file before reconciler.api is
imported, since api.py builds its module-level engine at import time (see
reconciler/db.py's make_engine default) -- setting it here keeps this suite
from touching a real reconciler.db or any configured Postgres instance.
"""

import os
import tempfile
import unittest

_fd, _DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.remove(_DB_PATH)
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"

from fastapi.testclient import TestClient

from reconciler import api

client = TestClient(api.app)


class TestGroundTruthEndpoint(unittest.TestCase):
  @classmethod
  def tearDownClass(cls):
    if os.path.exists(_DB_PATH):
      os.remove(_DB_PATH)

  def test_available_before_a_run(self):
    created = client.post("/batches", json={"seed": 1}).json()
    resp = client.get(f"/batches/{created['batch_id']}/ground_truth")
    self.assertEqual(resp.status_code, 200)
    ground_truth = resp.json()["ground_truth"]
    self.assertEqual(len(ground_truth), created["cases"])
    self.assertEqual(
      set(ground_truth[0]),
      {"case_id", "fault_type", "expected_decision", "expected_reason_category"})

  def test_unknown_batch_id_404s(self):
    resp = client.get("/batches/does-not-exist/ground_truth")
    self.assertEqual(resp.status_code, 404)

  def test_case_count_matches_the_run_it_scores(self):
    created = client.post("/batches", json={"seed": 2}).json()
    batch_id = created["batch_id"]
    client.post(f"/batches/{batch_id}/run")
    ground_truth = client.get(f"/batches/{batch_id}/ground_truth").json()["ground_truth"]
    run = client.get(f"/batches/{batch_id}").json()
    self.assertEqual(len(ground_truth), run["eval"]["total_cases"])

  def test_data_endpoint_still_excludes_ground_truth(self):
    created = client.post("/batches", json={"seed": 3}).json()
    data = client.get(f"/batches/{created['batch_id']}/data").json()
    self.assertNotIn("ground_truth", data)


if __name__ == "__main__":
  unittest.main()
