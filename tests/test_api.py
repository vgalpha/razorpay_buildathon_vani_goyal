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


class TestAskEndpoint(unittest.TestCase):
  """No test here may depend on network access or a real LLM key -- this
  suite runs with no LLM_* env var set, so every answer takes the
  deterministic-template path (source "template"). The LLM-configured path
  itself is covered in tests/test_qa.py and tests/test_llm.py, which don't
  need a live server.
  """

  def test_answer_has_a_source_field(self):
    created = client.post("/batches", json={"seed": 4}).json()
    batch_id = created["batch_id"]
    client.post(f"/batches/{batch_id}/run")
    resp = client.post(f"/batches/{batch_id}/ask", json={"question": "what's the match rate?"})
    self.assertEqual(resp.status_code, 200)
    body = resp.json()
    self.assertEqual(body["source"], "template")
    self.assertIn("cases processed", body["answer"])

  def test_requires_a_run_first(self):
    created = client.post("/batches", json={"seed": 5}).json()
    resp = client.post(f"/batches/{created['batch_id']}/ask", json={"question": "what broke?"})
    self.assertEqual(resp.status_code, 400)


def tearDownModule():
  # Single owner of the shared SQLite file's cleanup -- runs once after every
  # test in this module regardless of class order (unittest loads classes
  # alphabetically within a module, so a per-class tearDownClass here would
  # delete the file out from under a class that hasn't run yet).
  if os.path.exists(_DB_PATH):
    os.remove(_DB_PATH)


if __name__ == "__main__":
  unittest.main()
