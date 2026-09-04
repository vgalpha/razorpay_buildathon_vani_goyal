"""Record shapes mirroring Razorpay's documented Payment and Settlement Recon
entities (see /docs/api/payments/fetch-with-id and /docs/api/settlements/fetch-recon).

Fee rates below are illustrative placeholders for the synthetic dataset, not
Razorpay's published pricing.
"""

from dataclasses import dataclass, field
from typing import Optional

FEE_RATE_BY_METHOD = {
  "card": 0.020,
  "upi": 0.003,
  "netbanking": 0.019,
  "wallet": 0.015,
}
GST_ON_FEE = 0.18

HIGH_VALUE_THRESHOLD_PAISE = 50_000_00
ROUNDING_TOLERANCE_PAISE = 1_00


@dataclass
class Payment:
  id: str
  order_id: str
  amount: int
  currency: str
  method: str
  fee: int
  tax: int
  captured: bool
  amount_refunded: int
  dispute_id: Optional[str]
  created_at: int
  customer_id: str = ""

  def net_expected(self) -> int:
    return self.amount - self.fee - self.tax


@dataclass
class Invoice:
  """A books/ledger entry -- a separate, less-integrated system than the
  gateway. Deliberately matched by customer_id + amount only (not order_id),
  mirroring how a real accounting system often can't cross-reference the
  gateway's internal order_id. That looseness is what makes the
  duplicate-invoice collision case possible; see engine.py.
  """
  id: str
  customer_id: str
  amount: int
  order_id: Optional[str]
  status: str  # "open" -- awaiting a matching payment
  created_at: int


@dataclass
class SettlementLine:
  entity_id: str
  type: str
  amount: int
  currency: str
  fee: int
  tax: int
  settled: bool
  settlement_id: str
  settlement_utr: str
  payment_id: Optional[str]
  order_id: Optional[str]
  method: str
  dispute_id: Optional[str]
  created_at: int
  settled_at: int


@dataclass
class GroundTruthCase:
  case_id: str
  fault_type: str
  expected_decision: str
  expected_reason_category: str
