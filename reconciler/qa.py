"""Deterministic Q&A layer over an already-computed run + eval.

Every answer is computed from real data by plain Python first; only the
final phrasing goes through notes.rephrase (template by default, optional
LLM polish, never the source of a fact). Intent matching is a small fixed
set of keyword/pattern checks -- there is no free-form reasoning here on
purpose, matching the same "deterministic computes, LLM only phrases"
principle used throughout this project.
"""

import re
from typing import Dict, List, Optional

from .engine import Decision, ReconciliationRun
from .evaluate import EvalReport
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


def answer(question: str, run: ReconciliationRun, ev: EvalReport,
           payments: Optional[List[Payment]] = None) -> str:
  q = question.lower()
  if "match rate" in q or "accuracy" in q:
    return _answer_match_rate(ev)
  if "why" in q and _ID_PATTERN.search(question):
    return _answer_why(question, run)
  if "fast" in q or "throughput" in q or "how long" in q:
    return _answer_throughput(ev)
  if "biggest" in q or "largest" in q:
    return _answer_biggest_exception(run, payments or [])
  if "refuse" in q or "abstain" in q or "won't guess" in q or "never guess" in q:
    return _answer_abstention(run)
  if "broke" in q or "exception" in q:
    return _answer_exceptions(run)
  return ("I don't have a canned answer for that yet -- try asking about "
          "match rate, exceptions, throughput, the biggest exception, what "
          "it refuses to guess on, or a specific case id.")
