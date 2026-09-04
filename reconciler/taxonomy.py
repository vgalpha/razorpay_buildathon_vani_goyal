"""Single source of truth for the fault taxonomy.

Both the synthetic generator and the matching engine are checked against this
spec independently (generator via ground truth it emits, engine via
tests/test_engine.py using hand-built minimal cases). Neither file's own idea
of "correct" is the reference -- this one is. That is what keeps the eval from
becoming circular if the generator and the engine happen to share a bug.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FaultSpec:
  fault_type: str
  description: str
  expected_decision: str  # "auto_close" | "escalate" | "quarantine"
  expected_reason_category: str
  count: int


_SPECS = [
  FaultSpec(
    "clean_match", "Payment and settlement agree exactly.",
    "auto_close", "clean_match", 40),
  FaultSpec(
    "rounding_noise", "Settlement differs from expected net by a few paise.",
    "auto_close", "rounding_noise", 15),
  FaultSpec(
    "amount_mismatch", "Settlement differs from expected net beyond tolerance.",
    "escalate", "amount_mismatch", 15),
  FaultSpec(
    "multi_payment_ambiguous",
    "Order has multiple payments; recon payment-lines carry order_id only "
    "(no payment_id), so a line cannot be attributed to one specific payment.",
    "escalate", "multi_payment_ambiguous", 15),
  FaultSpec(
    "missing_settlement", "Payment captured but no matching recon line found.",
    "escalate", "missing_settlement", 12),
  FaultSpec(
    "duplicate_settlement", "More than one recon line for a single payment.",
    "escalate", "duplicate_settlement", 10),
  FaultSpec(
    "refund_clean", "Refund line amount matches payment.amount_refunded.",
    "auto_close", "refund_clean", 10),
  FaultSpec(
    "refund_mismatch", "Refund line amount does not match amount_refunded.",
    "escalate", "refund_mismatch", 8),
  FaultSpec(
    "disputed", "A dispute_id is present; never auto-close regardless of amount.",
    "escalate", "disputed", 8),
  FaultSpec(
    "high_value_gate",
    "Otherwise clean match, but amount exceeds the auto-close ceiling.",
    "escalate", "high_value_gate", 10),
  FaultSpec(
    "international_fx",
    "Cross-border payment settled in INR after FX conversion. The engine has "
    "no FX model: it safely escalates (never mis-closes) but can only label "
    "it a generic amount mismatch, not the true FX cause. Disclosed gap.",
    "escalate", "amount_mismatch", 10),
  FaultSpec(
    "quarantine",
    "Structurally malformed input (missing order_id, non-positive amount, "
    "unparseable created_at). Isolated at ingest before any matching logic "
    "runs; the run reports it and continues instead of crashing.",
    "quarantine", "quarantine", 5),
  FaultSpec(
    "books_clean_match",
    "Payment settles cleanly gateway-side (payments+settlements agree) and "
    "ties to exactly one open invoice for the same customer and amount.",
    "auto_close", "books_clean_match", 22),
  FaultSpec(
    "books_duplicate_invoice_collision",
    "Gateway settles cleanly, but more than one open invoice exists for the "
    "same customer at the same amount. Books-matching alone cannot say which "
    "invoice this payment settles, so the engine abstains rather than "
    "guessing -- the books-side twin of multi_payment_ambiguous.",
    "escalate", "books_duplicate_invoice_collision", 11),
  FaultSpec(
    "books_missing_invoice",
    "Gateway settles cleanly, but no open invoice exists in the books for "
    "this customer/amount at all -- a common real finance-ops gap (the "
    "invoice was simply never raised).",
    "escalate", "books_missing_invoice", 8),
  FaultSpec(
    "books_amount_mismatch",
    "Gateway settles cleanly, an invoice exists for the same customer, but "
    "its amount does not match the payment.",
    "escalate", "books_amount_mismatch", 8),
]

TAXONOMY = {spec.fault_type: spec for spec in _SPECS}
