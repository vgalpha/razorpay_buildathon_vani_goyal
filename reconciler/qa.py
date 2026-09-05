"""Deterministic Q&A layer over an already-computed run + eval.

Every answer is computed from real data by plain Python first; only the
final phrasing goes through notes.rephrase (template by default, optional
LLM polish, never the source of a fact). Intent matching is a small fixed
set of keyword/pattern checks -- there is no free-form reasoning for a
recognized intent, matching the same "deterministic computes, LLM only
phrases" principle used throughout this project.

The one exception is an unrecognized question: if an LLM provider is
configured (see llm.py), _llm_fallback below answers it directly instead of
the static "I don't have a canned answer" message -- but only from the
already-computed aggregate summary (never raw payment/settlement/invoice
records), and the caller marks that answer's source as "llm" so the UI can
disclose it, rather than letting it blend in with an already-true templated
fact the way notes.rephrase's polish deliberately does.
"""

import re
from typing import Dict, List, Optional, Tuple

from .engine import Decision, ReconciliationRun
from .evaluate import EvalReport
from .llm import call_llm, is_configured
from .notes import generate_note, rephrase
from .schema import Payment

ABSTENTION_CLASSES = {"multi_payment_ambiguous", "books_duplicate_invoice_collision"}

_ID_PATTERN = re.compile(r"\b(pay_|order_|recon_|inv_|setl_)\w+\b")


def _money(paise: float) -> str:
  return f"₹{paise/100:,.2f}"


def _amounts_by_id(payments: List[Payment]) -> Dict[str, int]:
  by_id = {}
  for p in payments:
    by_id[p.id] = p.amount
    by_id.setdefault(p.order_id, p.amount)
  return by_id


def _find_case(identifier: str, run: ReconciliationRun) -> Optional[Decision]:
  for d in run.decisions:
    if d.case_id == identifier or identifier in d.record_ids:
      return d
  return None


def _answer_match_rate(ev: EvalReport) -> str:
  return rephrase(
    f"{ev.total_cases} cases processed. Overall decision accuracy against "
    f"ground truth: {ev.overall_accuracy*100:.1f}%. False auto-close rate: "
    f"{ev.false_auto_close_rate*100:.2f}% -- that's the headline safety "
    f"number, and it should read as close to zero as possible.")


def _answer_exceptions(run: ReconciliationRun) -> str:
  escalated = [d for d in run.decisions if d.decision == "escalate"]
  if not escalated:
    return rephrase("No exceptions in this run -- every case auto-closed.")
  by_cat: Dict[str, int] = {}
  for d in escalated:
    by_cat[d.reason_category] = by_cat.get(d.reason_category, 0) + 1
  parts = ", ".join(f"{n} {cat}" for cat, n in sorted(by_cat.items()))
  return rephrase(f"{len(escalated)} exceptions open: {parts}.")


def _answer_why(question: str, run: ReconciliationRun) -> str:
  match = _ID_PATTERN.search(question)
  if not match:
    return rephrase(
      "I couldn't find a case id in that question -- ask about a specific "
      "pay_/order_/inv_/recon_/setl_ id.")
  decision = _find_case(match.group(0), run)
  if decision is None:
    return rephrase(f"No case found for {match.group(0)} in this run.")
  return generate_note(decision)


def _answer_throughput(ev: EvalReport) -> str:
  return rephrase(
    f"This run reconciled {ev.total_cases} cases in "
    f"{ev.wall_time_seconds*1000:.2f}ms -- about "
    f"{ev.throughput_per_sec:,.0f} records/sec. That's pure deterministic "
    f"comparison time; it will drop once real LLM calls are in the loop for "
    f"explanations, which is expected and fine since those are off the "
    f"decision path.")


def _answer_biggest_exception(run: ReconciliationRun,
                                payments: List[Payment]) -> str:
  escalated = [d for d in run.decisions if d.decision == "escalate"]
  if not escalated or not payments:
    return rephrase("No escalated cases with amount data available.")
  by_id = _amounts_by_id(payments)
  biggest = max(escalated, key=lambda d: by_id.get(d.case_id, 0))
  amount = by_id.get(biggest.case_id, 0)
  return rephrase(
    f"The largest open exception is {biggest.case_id} at "
    f"{_money(amount)}, reason: {biggest.reason_category}.")


def _answer_abstention(run: ReconciliationRun) -> str:
  abstained = [d for d in run.decisions if d.reason_category in ABSTENTION_CLASSES]
  if not abstained:
    return rephrase(
      "The engine refuses to guess on two structural cases: an order with "
      "multiple payments (a settlement line can't be attributed to one "
      "specific payment), and multiple open invoices matching the same "
      "customer and amount. Neither occurred in this run.")
  return rephrase(
    f"The engine never guesses on {len(abstained)} case(s) in this run: "
    "orders with multiple payments, and duplicate-matching open invoices. "
    "Both are schema-level ambiguities, not confidence judgments, so no "
    "amount of certainty would let it safely pick one.")


def _llm_fallback(question: str, run: ReconciliationRun,
                   ev: EvalReport) -> Optional[str]:
  """Answers a question that matched none of the fixed intents above, using
  only the aggregate run/eval summary -- never a raw payment, settlement, or
  invoice record. Returns None (never raises) on missing config or any
  failure, so the caller always has the static fallback to use instead."""
  if not is_configured():
    return None
  by_cat: Dict[str, int] = {}
  for d in run.decisions:
    by_cat[d.reason_category] = by_cat.get(d.reason_category, 0) + 1
  summary = (
    f"total_cases={ev.total_cases}, "
    f"overall_accuracy={ev.overall_accuracy*100:.1f}%, "
    f"false_auto_close_rate={ev.false_auto_close_rate*100:.2f}%, "
    f"auto_close_precision={ev.auto_close_precision*100:.1f}%, "
    f"auto_close_recall={ev.auto_close_recall*100:.1f}%, "
    f"throughput_per_sec={ev.throughput_per_sec:,.0f}, "
    f"decision_counts_by_reason_category={by_cat}")
  prompt = (
    "You are answering a question about one already-completed payment "
    "reconciliation run, for a finance-ops reviewer. You are given only the "
    "aggregate summary numbers below -- you have no access to individual "
    "payment, settlement, or invoice records, and must never invent one. If "
    "the question needs a fact not in this summary (e.g. a specific case id "
    "or a raw record), say plainly that you don't have that level of detail "
    "here and suggest checking the Exceptions / drill-down view instead. "
    "Never state a specific number that isn't in the summary below. Answer "
    "in 1-3 plain sentences, no preamble.\n\n"
    f"Run summary: {summary}\n\nQuestion: {question}")
  try:
    result = call_llm(prompt).strip()
    return result or None
  except Exception:
    return None


def _route(question: str, run: ReconciliationRun, ev: EvalReport,
           payments: Optional[List[Payment]] = None) -> Tuple[str, str]:
  q = question.lower()
  if "match rate" in q or "accuracy" in q:
    return _answer_match_rate(ev), "template"
  if "why" in q and _ID_PATTERN.search(question):
    return _answer_why(question, run), "template"
  if "fast" in q or "throughput" in q or "how long" in q:
    return _answer_throughput(ev), "template"
  if "biggest" in q or "largest" in q:
    return _answer_biggest_exception(run, payments or []), "template"
  if "refuse" in q or "abstain" in q or "won't guess" in q or "never guess" in q:
    return _answer_abstention(run), "template"
  if "broke" in q or "exception" in q:
    return _answer_exceptions(run), "template"
  llm_answer = _llm_fallback(question, run, ev)
  if llm_answer:
    return llm_answer, "llm"
  return ("I don't have a canned answer for that yet -- try asking about "
          "match rate, exceptions, throughput, the biggest exception, what "
          "it refuses to guess on, or a specific case id."), "template"


def answer(question: str, run: ReconciliationRun, ev: EvalReport,
           payments: Optional[List[Payment]] = None) -> str:
  return _route(question, run, ev, payments)[0]


def answer_with_source(question: str, run: ReconciliationRun, ev: EvalReport,
                        payments: Optional[List[Payment]] = None) -> Tuple[str, str]:
  """Same as answer(), but also returns "template" or "llm" so the caller
  (the API layer) can disclose when an answer was freshly LLM-generated
  rather than one of the fixed templates above."""
  return _route(question, run, ev, payments)
