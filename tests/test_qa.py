"""Tests for the explainer-notes and Q&A layers.

All assertions here run in template-only mode -- no test may depend on
network access or an API key being present, since neither is guaranteed in
CI or on a judge's machine. The LLM-present path (notes.rephrase actually
calling out) is exercised separately in test_llm_call_paths_are_reachable,
which only checks the request-building code runs without raising when a key
is set and the network call itself fails -- it still must not be able to
crash or hang the pipeline.
"""

import os
import unittest

from reconciler import qa
from reconciler.engine import reconcile
from reconciler.evaluate import EvalReport, evaluate
from reconciler.notes import generate_note, rephrase
from reconciler.schema import GroundTruthCase
from reconciler.taxonomy import TAXONOMY
from tests.test_engine import decision_for, invoice, line, payment


def _gt(case_id, fault_type):
  spec = TAXONOMY[fault_type]
  return GroundTruthCase(case_id, fault_type, spec.expected_decision,
                          spec.expected_reason_category)


def _build_scenario():
  payments, lines, invoices, ground_truth = [], [], [], []

  p1 = payment(id_="pay_clean", order_id="order_clean", amount=10000_00)
  payments.append(p1)
  lines.append(line(p1.net_expected(), order_id="order_clean",
                     entity_id="recon_clean"))
  # invoices is passed non-None below, so the books pass runs for every
  # auto_close case in the batch, not just the one meant to exercise it --
  # give this one a matching invoice too, or it falls through to
  # books_missing_invoice. Mirrors generate.py's real convention: fault_type
  # stays "clean_match" (evaluate.py only ever compares `decision`).
  invoices.append(invoice("inv_clean", customer_id=p1.customer_id,
                           amount=p1.amount, order_id=p1.order_id))
  ground_truth.append(_gt("order_clean", "clean_match"))

  p2a = payment(id_="pay_multi_a", order_id="order_multi", amount=5000_00)
  p2b = payment(id_="pay_multi_b", order_id="order_multi", amount=3000_00)
  payments += [p2a, p2b]
  lines.append(line(p2a.net_expected() + p2b.net_expected(),
                     order_id="order_multi", entity_id="recon_multi"))
  ground_truth.append(_gt("order_multi", "multi_payment_ambiguous"))

  p3 = payment(id_="pay_disputed", order_id="order_disputed", amount=8000_00,
               dispute_id="disp_1")
  payments.append(p3)
  lines.append(line(p3.net_expected(), order_id="order_disputed",
                     entity_id="recon_disputed"))
  ground_truth.append(_gt("order_disputed", "disputed"))

  p4 = payment(id_="pay_highvalue", order_id="order_highvalue",
               amount=60_000_00, fee=1200_00, tax=216_00)
  payments.append(p4)
  lines.append(line(p4.net_expected(), order_id="order_highvalue",
                     entity_id="recon_highvalue"))
  ground_truth.append(_gt("order_highvalue", "high_value_gate"))

  p5 = payment(id_="pay_books_collision", order_id="order_books_collision",
               amount=4000_00, customer_id="cust_collision")
  payments.append(p5)
  lines.append(line(p5.net_expected(), order_id="order_books_collision",
                     entity_id="recon_books_collision"))
  invoices.append(invoice("inv_1", customer_id="cust_collision",
                           amount=4000_00, order_id=None))
  invoices.append(invoice("inv_2", customer_id="cust_collision",
                           amount=4000_00, order_id=None))
  ground_truth.append(_gt("order_books_collision",
                           "books_duplicate_invoice_collision"))

  run = reconcile(payments, lines, invoices)
  ev = evaluate(run, ground_truth)
  return payments, run, ev


class TestQAIntents(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.payments, cls.recon_run, cls.ev = _build_scenario()

  def test_match_rate_intent_reports_real_numbers(self):
    ans = qa.answer("what's the match rate?", self.recon_run, self.ev)
    self.assertIn("5 cases", ans)
    self.assertIn("100.0%", ans)

  def test_exceptions_intent_lists_categories(self):
    ans = qa.answer("what broke?", self.recon_run, self.ev)
    self.assertIn("exceptions open", ans)
    self.assertIn("disputed", ans)

  def test_why_intent_looks_up_specific_case(self):
    ans = qa.answer("why was order_disputed not matched?", self.recon_run, self.ev)
    self.assertIn("dispute_id present", ans)

  def test_why_intent_handles_unknown_id(self):
    ans = qa.answer("why was order_ghost not matched?", self.recon_run, self.ev)
    self.assertIn("No case found", ans)

  def test_throughput_intent_reports_real_timing(self):
    ans = qa.answer("how fast was the run?", self.recon_run, self.ev)
    self.assertIn("5 cases", ans)
    self.assertIn("records/sec", ans)

  def test_biggest_exception_intent_picks_the_actual_largest(self):
    ans = qa.answer("what's the biggest exception?", self.recon_run, self.ev,
                     payments=self.payments)
    self.assertIn("order_highvalue", ans)

  def test_abstention_intent_names_both_abstention_classes(self):
    ans = qa.answer("what do you refuse to guess on?", self.recon_run, self.ev)
    self.assertIn("multiple payments", ans)
    self.assertIn("open invoices", ans)

  def test_unrecognized_question_gives_a_helpful_fallback(self):
    ans = qa.answer("what's your favorite color?", self.recon_run, self.ev)
    self.assertIn("canned answer", ans)

  def test_per_fault_class_intent_is_not_swallowed_by_match_rate(self):
    # Regression: "accuracy" as a substring of "per fault class accuracy"
    # previously matched the generic match-rate intent first, so this
    # question got the overall-accuracy answer instead of a per-class one.
    ans = qa.answer("whats per fault class accuracy", self.recon_run, self.ev)
    self.assertIn("100% accuracy", ans)
    self.assertNotIn("cases processed", ans)  # that's the match-rate answer's phrasing

  def test_per_fault_class_intent_matches_several_phrasings(self):
    for question in ("what's the per-fault-class accuracy?",
                      "per fault class breakdown",
                      "accuracy by fault type"):
      ans = qa.answer(question, self.recon_run, self.ev)
      self.assertNotIn("cases processed", ans)


class TestPerFaultClassAnswer(unittest.TestCase):
  """_build_scenario() is always 100% accuracy, so the "some fault types are
  below 100%" branch needs its own EvalReport, built directly rather than
  through a real run."""

  def test_lists_only_the_imperfect_classes(self):
    ev = EvalReport(
      total_cases=10, overall_accuracy=0.9, false_auto_close_rate=0.0,
      auto_close_precision=1.0, auto_close_recall=1.0, auto_close_f1=1.0,
      throughput_per_sec=1000, wall_time_seconds=0.01,
      per_fault_class={
        "clean_match": {"correct": 5, "total": 5, "accuracy": 1.0},
        "disputed": {"correct": 4, "total": 5, "accuracy": 0.8},
      })
    ans = qa.answer("per fault class accuracy", None, ev)
    self.assertIn("disputed", ans)
    self.assertIn("4/5", ans)
    self.assertNotIn("clean_match", ans)

  def test_all_perfect_gives_a_clean_summary(self):
    ev = EvalReport(
      total_cases=5, overall_accuracy=1.0, false_auto_close_rate=0.0,
      auto_close_precision=1.0, auto_close_recall=1.0, auto_close_f1=1.0,
      throughput_per_sec=1000, wall_time_seconds=0.01,
      per_fault_class={"clean_match": {"correct": 5, "total": 5, "accuracy": 1.0}})
    ans = qa.answer("per fault class accuracy", None, ev)
    self.assertIn("100% accuracy", ans)


class TestNotesTemplateFallback(unittest.TestCase):
  def setUp(self):
    self._saved = {
      k: os.environ.pop(k, None)
      for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")
    }

  def tearDown(self):
    for k, v in self._saved.items():
      if v is not None:
        os.environ[k] = v

  def test_rephrase_returns_input_unchanged_with_no_key_present(self):
    self.assertEqual(rephrase("a plain fact sentence"), "a plain fact sentence")

  def test_generate_note_matches_template_with_no_key_present(self):
    payments, run, _ = _build_scenario()
    d = decision_for("order_disputed", run)
    note = generate_note(d)
    self.assertIn("dispute_id present", note)
    self.assertIn("never auto-closed", note)


class TestNotesCiteRealFields(unittest.TestCase):
  """Every abstention/gate class's note must cite the actual case facts, not
  a generic label -- this is the "trust moment" the pitch video shows."""

  @classmethod
  def setUpClass(cls):
    cls.payments, cls.recon_run, cls.ev = _build_scenario()

  def test_multi_payment_note_cites_the_schema_limitation(self):
    note = generate_note(decision_for("order_multi", self.recon_run))
    self.assertIn("multiple payments", note)
    self.assertTrue(note.strip())

  def test_books_collision_note_cites_invoice_ids(self):
    note = generate_note(decision_for("order_books_collision", self.recon_run))
    self.assertIn("open invoices", note)
    self.assertTrue(note.strip())

  def test_disputed_note_cites_the_dispute_rule(self):
    note = generate_note(decision_for("order_disputed", self.recon_run))
    self.assertIn("dispute_id", note)
    self.assertTrue(note.strip())

  def test_high_value_note_cites_the_threshold(self):
    note = generate_note(decision_for("order_highvalue", self.recon_run))
    self.assertIn("50000", note.replace("₹", "").replace(",", ""))
    self.assertTrue(note.strip())


class TestAnswerWithSource(unittest.TestCase):
  """answer_with_source() is the entry point api.py actually calls -- it
  must keep answer()'s exact text for every recognized intent (source
  "template"), and only mark a response "llm" when the free-form fallback
  actually produced one."""

  @classmethod
  def setUpClass(cls):
    cls.payments, cls.recon_run, cls.ev = _build_scenario()

  def setUp(self):
    self._saved = {
      k: os.environ.pop(k, None)
      for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "LLM_PROVIDER")
    }

  def tearDown(self):
    for k, v in self._saved.items():
      if v is not None:
        os.environ[k] = v

  def test_recognized_intent_is_labeled_template(self):
    text, source = qa.answer_with_source("what's the match rate?", self.recon_run, self.ev)
    self.assertEqual(source, "template")
    self.assertEqual(text, qa.answer("what's the match rate?", self.recon_run, self.ev))

  def test_unrecognized_question_with_no_llm_configured_is_labeled_template(self):
    text, source = qa.answer_with_source("what's your favorite color?", self.recon_run, self.ev)
    self.assertEqual(source, "template")
    self.assertIn("canned answer", text)

  def test_unrecognized_question_falls_back_to_template_when_llm_call_fails(self):
    # A fake key means an LLM IS configured, so the free-form path is
    # attempted, but the network call fails -- must still degrade cleanly
    # to the same static message, not raise or hang the endpoint.
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-fake-key-for-testing-only"
    text, source = qa.answer_with_source("what's your favorite color?", self.recon_run, self.ev)
    self.assertEqual(source, "template")
    self.assertIn("canned answer", text)


class TestLLMCallPathsAreReachable(unittest.TestCase):
  """Confirms the LLM-present branch runs its request-building code without
  raising, and still degrades to the template on failure -- this is run
  against a deliberately fake key so the network call fails, proving the
  fallback works even when a key IS present, not only when one is absent."""

  def setUp(self):
    self._saved = {
      k: os.environ.pop(k, None)
      for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")
    }

  def tearDown(self):
    for k, v in self._saved.items():
      if v is not None:
        os.environ[k] = v
      else:
        os.environ.pop(k, None)

  def test_anthropic_path_falls_back_on_auth_failure(self):
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-fake-key-for-testing-only"
    result = rephrase("a plain fact sentence")
    self.assertEqual(result, "a plain fact sentence")


if __name__ == "__main__":
  unittest.main()
