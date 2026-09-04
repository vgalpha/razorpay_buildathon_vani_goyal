"""Deterministic reconciliation engine.

Plain comparisons decide auto_close / escalate / quarantine. Nothing here
calls an LLM -- that is the entire point (see docs/ARCHITECTURE.md, "Core
principle"). Passes run in a fixed order per order_id group; first
applicable rule wins.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List

from .schema import FEE_RATE_BY_METHOD, HIGH_VALUE_THRESHOLD_PAISE, \
  ROUNDING_TOLERANCE_PAISE, Payment, SettlementLine, Invoice


@dataclass
class Decision:
  case_id: str
  decision: str  # auto_close | escalate | quarantine
  reason_category: str
  reason_detail: str
  rule: str
  record_ids: List[str]


@dataclass
class ReconciliationRun:
  decisions: List[Decision]
  pass_counts: Dict[str, int] = field(default_factory=dict)
  pass_timings_ms: Dict[str, float] = field(default_factory=dict)
  pass_hit_counts: Dict[str, int] = field(default_factory=dict)
  invariants: Dict[str, bool] = field(default_factory=dict)
  wall_time_seconds: float = 0.0


def _is_malformed(p: Payment) -> str:
  if not p.order_id:
    return "missing order_id"
  if not isinstance(p.amount, int) or p.amount <= 0:
    return "non-positive or non-numeric amount"
  if not isinstance(p.created_at, int):
    return "unparseable created_at"
  if p.method not in FEE_RATE_BY_METHOD:
    return "unknown payment method"
  return ""


def _quarantine_pass(payments):
  clean, decisions = [], []
  for p in payments:
    reason = _is_malformed(p)
    if reason:
      decisions.append(Decision(
        case_id=p.id, decision="quarantine", reason_category="quarantine",
        reason_detail=f"isolated at ingest: {reason}", rule="quarantine",
        record_ids=[p.id]))
    else:
      clean.append(p)
  return clean, decisions


def _group_by_order(payments):
  groups = defaultdict(list)
  for p in payments:
    groups[p.order_id].append(p)
  return groups


def _index_invoices(invoices):
  """Deliberately keyed by (customer_id, amount) only, never order_id -- a
  books/ledger system in practice often can't cross-reference the gateway's
  order_id. That looseness is what makes the duplicate-invoice collision
  possible, and it's the point of this leg, not an oversight."""
  by_customer_amount = defaultdict(list)
  by_customer = defaultdict(list)
  for inv in invoices:
    if inv.status != "open":
      continue
    by_customer_amount[(inv.customer_id, inv.amount)].append(inv)
    by_customer[inv.customer_id].append(inv)
  return by_customer_amount, by_customer


def _apply_books_check(decision, payment, by_customer_amount, by_customer, consumed_invoices):
  exact = by_customer_amount.get((payment.customer_id, payment.amount), [])
  if len(exact) == 1:
    inv = exact[0]
    consumed_invoices.append(inv.id)
    return Decision(decision.case_id, "auto_close", "books_clean_match",
                     f"tied to invoice {inv.id} for the same customer and amount",
                     "books_customer_amount", decision.record_ids + [inv.id])
  if len(exact) > 1:
    return Decision(decision.case_id, "escalate", "books_duplicate_invoice_collision",
                     f"{len(exact)} open invoices match this customer and amount; "
                     "books alone cannot say which one this payment settles -- abstaining",
                     "books_customer_amount", decision.record_ids + [i.id for i in exact])
  candidates = by_customer.get(payment.customer_id, [])
  if candidates:
    inv = candidates[0]
    return Decision(decision.case_id, "escalate", "books_amount_mismatch",
                     f"invoice {inv.id} for this customer is ₹{inv.amount/100:.2f}, "
                     f"payment is ₹{payment.amount/100:.2f}",
                     "books_customer_amount", decision.record_ids + [inv.id])
  return Decision(decision.case_id, "escalate", "books_missing_invoice",
                   "payment settled cleanly gateway-side but no open invoice "
                   "found in the books for this customer",
                   "books_customer_amount", decision.record_ids)


def _index_lines(lines):
  by_order_payment_type = defaultdict(list)
  by_payment_id = defaultdict(list)
  for ln in lines:
    if ln.type == "payment":
      by_order_payment_type[ln.order_id].append(ln)
    elif ln.type == "refund":
      by_payment_id[ln.payment_id].append(ln)
  return by_order_payment_type, by_payment_id


def _amount_diff_decision(order_id, payment, line, consumed):
  consumed.add(line.entity_id)
  diff = abs(line.amount - payment.net_expected())
  detail = f"settlement ₹{line.amount/100:.2f} vs expected net ₹{payment.net_expected()/100:.2f}"
  if diff == 0:
    return Decision(order_id, "auto_close", "clean_match", detail,
                     "exact_net_match", [payment.id, line.entity_id])
  if diff <= ROUNDING_TOLERANCE_PAISE:
    return Decision(order_id, "auto_close", "rounding_noise",
                     f"{detail} (within ₹{ROUNDING_TOLERANCE_PAISE/100:.2f} tolerance)",
                     "rounding_tolerance", [payment.id, line.entity_id])
  return Decision(order_id, "escalate", "amount_mismatch",
                   f"{detail}, diff ₹{diff/100:.2f} exceeds tolerance",
                   "amount_tolerance", [payment.id, line.entity_id])


def _refund_decision(order_id, payment, refund_lines, consumed):
  line = refund_lines[0]
  consumed.add(line.entity_id)
  diff = abs(line.amount - payment.amount_refunded)
  detail = f"refund ₹{line.amount/100:.2f} vs amount_refunded ₹{payment.amount_refunded/100:.2f}"
  if diff <= ROUNDING_TOLERANCE_PAISE:
    return Decision(order_id, "auto_close", "refund_clean", detail,
                     "refund_match", [payment.id, line.entity_id])
  return Decision(order_id, "escalate", "refund_mismatch",
                   f"{detail}, diff ₹{diff/100:.2f}", "refund_match",
                   [payment.id, line.entity_id])


def _check_disputed(order_id, payments_in_order, by_order_payment_type, by_payment_id, consumed):
  disputed = any(p.dispute_id for p in payments_in_order) or any(
    ln.dispute_id for ln in by_order_payment_type.get(order_id, []))
  if not disputed:
    return None
  return Decision(order_id, "escalate", "disputed",
                   "dispute_id present; never auto-closed regardless of amount",
                   "disputed_gate", [p.id for p in payments_in_order])


def _check_high_value(order_id, payments_in_order, by_order_payment_type, by_payment_id, consumed):
  if not any(p.amount > HIGH_VALUE_THRESHOLD_PAISE for p in payments_in_order):
    return None
  return Decision(order_id, "escalate", "high_value_gate",
                   f"amount exceeds ₹{HIGH_VALUE_THRESHOLD_PAISE/100:.2f} auto-close ceiling",
                   "high_value_gate", [p.id for p in payments_in_order])


def _check_multi_payment(order_id, payments_in_order, by_order_payment_type, by_payment_id, consumed):
  if len(payments_in_order) <= 1:
    return None
  return Decision(order_id, "escalate", "multi_payment_ambiguous",
                   "order has multiple payments; recon payment-lines carry "
                   "order_id only (no payment_id), so a settlement line "
                   "cannot be attributed to one specific payment",
                   "multi_payment_schema_limit", [p.id for p in payments_in_order])


def _check_refund(order_id, payments_in_order, by_order_payment_type, by_payment_id, consumed):
  payment = payments_in_order[0]
  if payment.amount_refunded <= 0:
    return None
  refund_lines = by_payment_id.get(payment.id, [])
  if not refund_lines:
    return None
  return _refund_decision(order_id, payment, refund_lines, consumed)


def _check_settlement_match(order_id, payments_in_order, by_order_payment_type, by_payment_id, consumed):
  payment = payments_in_order[0]
  payment_lines = by_order_payment_type.get(order_id, [])
  if not payment_lines:
    return Decision(order_id, "escalate", "missing_settlement",
                     "payment captured but no matching settlement line found",
                     "missing_settlement", [payment.id])
  if len(payment_lines) > 1:
    return Decision(order_id, "escalate", "duplicate_settlement",
                     f"{len(payment_lines)} settlement lines found for one payment",
                     "duplicate_settlement", [payment.id] + [ln.entity_id for ln in payment_lines])
  return _amount_diff_decision(order_id, payment, payment_lines[0], consumed)


# Ordered per-order passes, first non-None result wins. _check_settlement_match
# is terminal (always returns a Decision) so every order resolves.
_ORDER_PASSES = [
  ("disputed", _check_disputed),
  ("high_value_gate", _check_high_value),
  ("multi_payment", _check_multi_payment),
  ("refund", _check_refund),
  ("settlement_match", _check_settlement_match),
]

# settlement_match covers two rubric-named passes ("exact/tolerance match" and
# "missing/duplicate settlement") behind one call site; its measured time is
# attributed to whichever bucket the resulting reason_category actually falls
# into, so the reported per-pass numbers stay honest without a second call.
_MISSING_DUPLICATE_REASONS = {"missing_settlement", "duplicate_settlement"}


def _order_decision(order_id, payments_in_order, by_order_payment_type,
                     by_payment_id, consumed, pass_timings, pass_hits):
  for name, check in _ORDER_PASSES:
    t0 = time.perf_counter()
    result = check(order_id, payments_in_order, by_order_payment_type, by_payment_id, consumed)
    elapsed = time.perf_counter() - t0
    if result is None:
      pass_timings[name] += elapsed
      continue
    bucket = name
    if name == "settlement_match":
      bucket = ("missing_duplicate_settlement"
                if result.reason_category in _MISSING_DUPLICATE_REASONS
                else "exact_tolerance_match")
    pass_timings[bucket] += elapsed
    pass_hits[bucket] += 1
    return result
  raise AssertionError("no pass resolved a decision -- settlement_match should be terminal")


def reconcile(payments: List[Payment], settlement_lines: List[SettlementLine],
              invoices: List[Invoice] = None) -> ReconciliationRun:
  """invoices=None (the default) skips the books-matching pass entirely --
  this keeps every pre-books-leg caller (including the 2-source unit tests)
  behaviorally unchanged. Passing a list, even an empty one, means books data
  was genuinely collected for this batch and enables the third leg."""
  start = time.perf_counter()
  decisions: List[Decision] = []
  pass_counts: Dict[str, int] = defaultdict(int)
  pass_timings: Dict[str, float] = defaultdict(float)
  pass_hits: Dict[str, int] = defaultdict(int)
  consumed = set()
  consumed_invoices: List[str] = []
  books_enabled = invoices is not None

  t0 = time.perf_counter()
  clean_payments, quarantine_decisions = _quarantine_pass(payments)
  pass_timings["quarantine"] += time.perf_counter() - t0
  pass_hits["quarantine"] += len(quarantine_decisions)
  decisions.extend(quarantine_decisions)
  pass_counts["quarantine"] += len(quarantine_decisions)

  by_order_payment_type, by_payment_id = _index_lines(settlement_lines)
  by_customer_amount, by_customer = _index_invoices(invoices or [])
  for order_id, payments_in_order in _group_by_order(clean_payments).items():
    d = _order_decision(order_id, payments_in_order, by_order_payment_type,
                         by_payment_id, consumed, pass_timings, pass_hits)
    if books_enabled and d.decision == "auto_close":
      t0 = time.perf_counter()
      d = _apply_books_check(d, payments_in_order[0], by_customer_amount,
                              by_customer, consumed_invoices)
      pass_timings["books_customer_amount"] += time.perf_counter() - t0
      pass_hits["books_customer_amount"] += 1
    decisions.append(d)
    pass_counts[d.rule] += 1

  run = ReconciliationRun(
    decisions=decisions, pass_counts=dict(pass_counts),
    pass_timings_ms={k: v * 1000 for k, v in pass_timings.items()},
    pass_hit_counts=dict(pass_hits))
  run.invariants = _check_invariants(run, payments, consumed_invoices)
  run.wall_time_seconds = time.perf_counter() - start
  return run


def _check_invariants(run: ReconciliationRun, payments: List[Payment],
                       consumed_invoices: List[str]) -> Dict[str, bool]:
  case_ids = [d.case_id for d in run.decisions]
  no_duplicate_cases = len(case_ids) == len(set(case_ids))
  expected_case_count = len({p.order_id for p in payments if _is_malformed(p) == ""} |
                             {p.id for p in payments if _is_malformed(p) != ""})
  # multi-payment orders share one case_id, so distinct case count, not
  # payment count, is what must equal the decision count.
  coverage_complete = len(set(case_ids)) == expected_case_count
  decision_total_conserved = (
    sum(1 for d in run.decisions if d.decision == "auto_close") +
    sum(1 for d in run.decisions if d.decision == "escalate") +
    sum(1 for d in run.decisions if d.decision == "quarantine")
  ) == len(run.decisions)
  no_invoice_double_consumed = len(consumed_invoices) == len(set(consumed_invoices))
  return {
    "no_duplicate_case_decisions": no_duplicate_cases,
    "every_case_covered_exactly_once": coverage_complete,
    "decision_counts_conserve_total": decision_total_conserved,
    "no_invoice_double_consumed": no_invoice_double_consumed,
  }
