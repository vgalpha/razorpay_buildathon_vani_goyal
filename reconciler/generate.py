"""Synthetic batch generator.

Builds payments + settlement recon lines for every fault class in
TAXONOMY, using each class's exact `count` (not probability sampling), and
emits ground truth sourced directly from TAXONOMY -- never reinvented here.
A fixed seed keeps a run reproducible. order_ids come from orders_source,
which is the single place that knows whether they're real (mode="live") or
synthetic (mode="synthetic", the default).
"""

import random
import string
from dataclasses import dataclass
from typing import List

from .schema import FEE_RATE_BY_METHOD, GST_ON_FEE, HIGH_VALUE_THRESHOLD_PAISE, \
  ROUNDING_TOLERANCE_PAISE, Payment, SettlementLine, GroundTruthCase, Invoice
from .taxonomy import TAXONOMY
from . import orders_source

SEED = 42
BASE_TS = 1_735_000_000
METHODS = list(FEE_RATE_BY_METHOD)
TOTAL_ORDERS_NEEDED = sum(spec.count for spec in TAXONOMY.values())


@dataclass
class Dataset:
  payments: List[Payment]
  settlement_lines: List[SettlementLine]
  ground_truth: List[GroundTruthCase]
  invoices: List[Invoice]


def _rand_id(rng, prefix, n=14):
  chars = string.ascii_letters + string.digits
  return prefix + "".join(rng.choice(chars) for _ in range(n))


def _fee_tax(amount, method):
  fee = round(amount * FEE_RATE_BY_METHOD[method])
  tax = round(fee * GST_ON_FEE)
  return fee, tax


def _payment(rng, amount, method, order_id, dispute_id=None,
             amount_refunded=0, created_at=BASE_TS, customer_id=None):
  fee, tax = _fee_tax(amount, method)
  return Payment(
    id=_rand_id(rng, "pay_"), order_id=order_id,
    amount=amount, currency="INR", method=method, fee=fee, tax=tax,
    captured=True, amount_refunded=amount_refunded, dispute_id=dispute_id,
    created_at=created_at, customer_id=customer_id or _rand_id(rng, "cust_"))


def _line(rng, amount, method, order_id, fee=0, tax=0, payment_id=None,
          type_="payment", dispute_id=None, created_at=BASE_TS):
  return SettlementLine(
    entity_id=_rand_id(rng, "recon_"), type=type_, amount=amount,
    currency="INR", fee=fee, tax=tax, settled=True,
    settlement_id=_rand_id(rng, "setl_"), settlement_utr=_rand_id(rng, "utr_", 10),
    payment_id=payment_id, order_id=order_id, method=method,
    dispute_id=dispute_id, created_at=created_at, settled_at=created_at + 2 * 86400)


def _gt(order_id, fault_type):
  spec = TAXONOMY[fault_type]
  return GroundTruthCase(order_id, fault_type, spec.expected_decision,
                          spec.expected_reason_category)


def _add_invoice(rng, ds, customer_id, amount, order_id, status="open"):
  ds.invoices.append(Invoice(
    id=_rand_id(rng, "inv_"), customer_id=customer_id, amount=amount,
    order_id=order_id, status=status, created_at=BASE_TS))


def _add_clean_style_case(rng, ds, order_id, fault_type, diff_fn, attach_invoice=False):
  amount = rng.randint(100_00, 40_000_00)
  method = rng.choice(METHODS)
  p = _payment(rng, amount, method, order_id)
  settled = p.net_expected() + diff_fn(rng)
  line = _line(rng, settled, method, p.order_id, fee=p.fee, tax=p.tax)
  ds.payments.append(p)
  ds.settlement_lines.append(line)
  ds.ground_truth.append(_gt(p.order_id, fault_type))
  if attach_invoice:
    _add_invoice(rng, ds, p.customer_id, p.amount, p.order_id)


def _build_clean_match(rng, ds, n, orders):
  for _ in range(n):
    _add_clean_style_case(rng, ds, next(orders), "clean_match", lambda r: 0,
                           attach_invoice=True)


def _build_rounding_noise(rng, ds, n, orders):
  for _ in range(n):
    diff = lambda r: r.choice([-1, 1]) * r.randint(1, ROUNDING_TOLERANCE_PAISE)
    _add_clean_style_case(rng, ds, next(orders), "rounding_noise", diff,
                           attach_invoice=True)


def _build_amount_mismatch(rng, ds, n, orders):
  for _ in range(n):
    diff = lambda r: r.choice([-1, 1]) * r.randint(
      ROUNDING_TOLERANCE_PAISE + 100, ROUNDING_TOLERANCE_PAISE + 3000)
    _add_clean_style_case(rng, ds, next(orders), "amount_mismatch", diff)


def _build_multi_payment_ambiguous(rng, ds, n, orders):
  for _ in range(n):
    order_id = next(orders)
    total = 0
    method = None
    for _ in range(2):
      amount = rng.randint(100_00, 20_000_00)
      method = rng.choice(METHODS)
      p = _payment(rng, amount, method, order_id)
      ds.payments.append(p)
      total += p.net_expected()
    ds.settlement_lines.append(_line(rng, total, method, order_id))
    ds.ground_truth.append(_gt(order_id, "multi_payment_ambiguous"))


def _build_missing_settlement(rng, ds, n, orders):
  for _ in range(n):
    amount = rng.randint(100_00, 40_000_00)
    method = rng.choice(METHODS)
    p = _payment(rng, amount, method, next(orders))
    ds.payments.append(p)
    ds.ground_truth.append(_gt(p.order_id, "missing_settlement"))


def _build_duplicate_settlement(rng, ds, n, orders):
  for _ in range(n):
    amount = rng.randint(100_00, 40_000_00)
    method = rng.choice(METHODS)
    p = _payment(rng, amount, method, next(orders))
    ds.payments.append(p)
    for _ in range(2):
      ds.settlement_lines.append(_line(rng, p.net_expected(), method, p.order_id))
    ds.ground_truth.append(_gt(p.order_id, "duplicate_settlement"))


def _build_refund(rng, ds, n, orders, clean):
  for _ in range(n):
    amount = rng.randint(100_00, 20_000_00)
    method = rng.choice(METHODS)
    p = _payment(rng, amount, method, next(orders), amount_refunded=amount)
    ds.payments.append(p)
    diff = 0 if clean else rng.randint(ROUNDING_TOLERANCE_PAISE + 100,
                                        ROUNDING_TOLERANCE_PAISE + 2000)
    line = _line(rng, amount + diff, method, p.order_id, payment_id=p.id,
                 type_="refund")
    ds.settlement_lines.append(line)
    ds.ground_truth.append(_gt(p.order_id, "refund_clean" if clean else "refund_mismatch"))
    if clean:
      _add_invoice(rng, ds, p.customer_id, p.amount, p.order_id)


def _build_disputed(rng, ds, n, orders):
  for _ in range(n):
    amount = rng.randint(100_00, 40_000_00)
    method = rng.choice(METHODS)
    p = _payment(rng, amount, method, next(orders), dispute_id=_rand_id(rng, "disp_"))
    line = _line(rng, p.net_expected(), method, p.order_id, fee=p.fee, tax=p.tax)
    ds.payments.append(p)
    ds.settlement_lines.append(line)
    ds.ground_truth.append(_gt(p.order_id, "disputed"))


def _build_high_value_gate(rng, ds, n, orders):
  for _ in range(n):
    amount = rng.randint(HIGH_VALUE_THRESHOLD_PAISE + 100_00, HIGH_VALUE_THRESHOLD_PAISE + 2_000_000)
    method = rng.choice(METHODS)
    p = _payment(rng, amount, method, next(orders))
    line = _line(rng, p.net_expected(), method, p.order_id, fee=p.fee, tax=p.tax)
    ds.payments.append(p)
    ds.settlement_lines.append(line)
    ds.ground_truth.append(_gt(p.order_id, "high_value_gate"))


def _build_international_fx(rng, ds, n, orders):
  for _ in range(n):
    amount = rng.randint(500_00, 30_000_00)
    method = rng.choice(METHODS)
    p = _payment(rng, amount, method, next(orders))
    fx_diff = round(amount * rng.uniform(0.05, 0.15)) * rng.choice([-1, 1])
    line = _line(rng, p.net_expected() + fx_diff, method, p.order_id, fee=p.fee, tax=p.tax)
    ds.payments.append(p)
    ds.settlement_lines.append(line)
    ds.ground_truth.append(_gt(p.order_id, "international_fx"))


def _build_quarantine(rng, ds, n, orders):
  malformations = [
    lambda p: setattr(p, "order_id", ""),
    lambda p: setattr(p, "amount", -abs(p.amount)),
    lambda p: setattr(p, "amount", "N/A"),
    lambda p: setattr(p, "created_at", "not-a-timestamp"),
    lambda p: setattr(p, "method", "carrier_pigeon"),
  ]
  for i in range(n):
    amount = rng.randint(100_00, 10_000_00)
    method = rng.choice(METHODS)
    p = _payment(rng, amount, method, next(orders))
    malformations[i % len(malformations)](p)
    ds.payments.append(p)
    ds.ground_truth.append(_gt(p.id, "quarantine"))


def _clean_gateway_pair(rng, ds, order_id, fault_type):
  """Builds a payment + settlement line that agree exactly, so the gateway
  side reaches auto_close and the case's fate is decided entirely by the
  books check that follows -- these classes exist to test that layer, not
  the gateway matcher. Returns the payment so callers can attach invoices."""
  amount = rng.randint(100_00, 30_000_00)
  method = rng.choice(METHODS)
  p = _payment(rng, amount, method, order_id)
  line = _line(rng, p.net_expected(), method, order_id, fee=p.fee, tax=p.tax)
  ds.payments.append(p)
  ds.settlement_lines.append(line)
  ds.ground_truth.append(_gt(order_id, fault_type))
  return p


def _build_books_clean_match(rng, ds, n, orders):
  for _ in range(n):
    order_id = next(orders)
    p = _clean_gateway_pair(rng, ds, order_id, "books_clean_match")
    _add_invoice(rng, ds, p.customer_id, p.amount, order_id)


def _build_books_duplicate_invoice_collision(rng, ds, n, orders):
  for _ in range(n):
    order_id = next(orders)
    p = _clean_gateway_pair(rng, ds, order_id, "books_duplicate_invoice_collision")
    # Two open invoices, same customer, same amount, no order_id link -- books
    # alone cannot say which one this payment settles. Abstain, don't guess.
    _add_invoice(rng, ds, p.customer_id, p.amount, order_id=None)
    _add_invoice(rng, ds, p.customer_id, p.amount, order_id=None)


def _build_books_missing_invoice(rng, ds, n, orders):
  for _ in range(n):
    order_id = next(orders)
    _clean_gateway_pair(rng, ds, order_id, "books_missing_invoice")
    # deliberately: no invoice raised for this customer/amount at all


def _build_books_amount_mismatch(rng, ds, n, orders):
  for _ in range(n):
    order_id = next(orders)
    p = _clean_gateway_pair(rng, ds, order_id, "books_amount_mismatch")
    diff = rng.randint(100_00, 500_00) * rng.choice([-1, 1])
    _add_invoice(rng, ds, p.customer_id, p.amount + diff, order_id=None)


_BUILDERS = {
  "clean_match": _build_clean_match,
  "rounding_noise": _build_rounding_noise,
  "amount_mismatch": _build_amount_mismatch,
  "multi_payment_ambiguous": _build_multi_payment_ambiguous,
  "missing_settlement": _build_missing_settlement,
  "duplicate_settlement": _build_duplicate_settlement,
  "refund_clean": lambda rng, ds, n, orders: _build_refund(rng, ds, n, orders, clean=True),
  "refund_mismatch": lambda rng, ds, n, orders: _build_refund(rng, ds, n, orders, clean=False),
  "disputed": _build_disputed,
  "high_value_gate": _build_high_value_gate,
  "international_fx": _build_international_fx,
  "quarantine": _build_quarantine,
  "books_clean_match": _build_books_clean_match,
  "books_duplicate_invoice_collision": _build_books_duplicate_invoice_collision,
  "books_missing_invoice": _build_books_missing_invoice,
  "books_amount_mismatch": _build_books_amount_mismatch,
}


def generate_dataset(seed=SEED, order_mode="synthetic") -> Dataset:
  rng = random.Random(seed)
  order_ids = orders_source.load_orders(
    TOTAL_ORDERS_NEEDED, mode=order_mode, seed=seed)
  orders = iter(order_ids)
  ds = Dataset(payments=[], settlement_lines=[], ground_truth=[], invoices=[])
  for fault_type, spec in TAXONOMY.items():
    _BUILDERS[fault_type](rng, ds, spec.count, orders)
  rng.shuffle(ds.payments)
  return ds
