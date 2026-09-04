"""Load-bearing test file.

Every case here is built BY HAND from taxonomy.py's prose description, not
by calling generate.py. This independence is the entire point: if the
generator and the engine ever shared a wrong assumption, these tests would
still catch it (see docs/ARCHITECTURE.md, "Testing philosophy").

Run: python3 -m unittest discover -s tests
"""

import unittest

from reconciler.engine import reconcile
from reconciler.schema import Payment, SettlementLine, Invoice
from reconciler.taxonomy import TAXONOMY

T0 = 1_700_000_000


def payment(id_="pay_1", order_id="order_1", amount=10000_00, method="card",
            fee=200_00, tax=36_00, captured=True, amount_refunded=0,
            dispute_id=None, created_at=T0, customer_id="cust_1"):
  return Payment(id=id_, order_id=order_id, amount=amount, currency="INR",
                  method=method, fee=fee, tax=tax, captured=captured,
                  amount_refunded=amount_refunded, dispute_id=dispute_id,
                  created_at=created_at, customer_id=customer_id)


def invoice(id_, customer_id="cust_1", amount=10000_00, order_id=None,
            status="open", created_at=T0):
  return Invoice(id=id_, customer_id=customer_id, amount=amount,
                  order_id=order_id, status=status, created_at=created_at)


def line(amount, order_id="order_1", type_="payment", payment_id=None,
         fee=0, tax=0, dispute_id=None, entity_id="recon_1",
         method="card", created_at=T0):
  return SettlementLine(entity_id=entity_id, type=type_, amount=amount,
                          currency="INR", fee=fee, tax=tax, settled=True,
                          settlement_id="setl_1", settlement_utr="utr_1",
                          payment_id=payment_id, order_id=order_id,
                          method=method, dispute_id=dispute_id,
                          created_at=created_at, settled_at=created_at + 172800)


def decision_for(order_or_payment_id, run):
  matches = [d for d in run.decisions if d.case_id == order_or_payment_id]
  assert len(matches) == 1, f"expected exactly one decision for {order_or_payment_id}"
  return matches[0]


class TestTaxonomyCoverage(unittest.TestCase):
  def test_every_fault_type_has_a_test_below(self):
    covered = {
      "clean_match", "rounding_noise", "amount_mismatch",
      "multi_payment_ambiguous", "missing_settlement", "duplicate_settlement",
      "refund_clean", "refund_mismatch", "disputed", "high_value_gate",
      "international_fx", "quarantine",
      "books_clean_match", "books_duplicate_invoice_collision",
      "books_missing_invoice", "books_amount_mismatch",
    }
    self.assertEqual(covered, set(TAXONOMY.keys()))


class TestEngineDecisions(unittest.TestCase):
  def test_clean_match_auto_closes(self):
    p = payment()
    run = reconcile([p], [line(p.net_expected())])
    d = decision_for("order_1", run)
    self.assertEqual(d.decision, TAXONOMY["clean_match"].expected_decision)
    self.assertEqual(d.reason_category, "clean_match")

  def test_rounding_noise_auto_closes(self):
    p = payment()
    run = reconcile([p], [line(p.net_expected() + 50)])  # 50 paise, within ₹1
    d = decision_for("order_1", run)
    self.assertEqual(d.decision, TAXONOMY["rounding_noise"].expected_decision)

  def test_amount_mismatch_escalates(self):
    p = payment()
    run = reconcile([p], [line(p.net_expected() + 500_00)])  # ₹500 off
    d = decision_for("order_1", run)
    self.assertEqual(d.decision, TAXONOMY["amount_mismatch"].expected_decision)
    self.assertEqual(d.reason_category, "amount_mismatch")

  def test_multi_payment_order_always_escalates_even_if_total_reconciles(self):
    p1 = payment(id_="pay_1", amount=5000_00, fee=100_00, tax=18_00)
    p2 = payment(id_="pay_2", amount=3000_00, fee=60_00, tax=11_00)
    total_net = p1.net_expected() + p2.net_expected()
    run = reconcile([p1, p2], [line(total_net)])  # totals tie out exactly
    d = decision_for("order_1", run)
    self.assertEqual(d.decision, TAXONOMY["multi_payment_ambiguous"].expected_decision)
    self.assertEqual(d.reason_category, "multi_payment_ambiguous")

  def test_missing_settlement_escalates(self):
    p = payment()
    run = reconcile([p], [])
    d = decision_for("order_1", run)
    self.assertEqual(d.decision, TAXONOMY["missing_settlement"].expected_decision)

  def test_duplicate_settlement_escalates(self):
    p = payment()
    run = reconcile([p], [
      line(p.net_expected(), entity_id="recon_1"),
      line(p.net_expected(), entity_id="recon_2"),
    ])
    d = decision_for("order_1", run)
    self.assertEqual(d.decision, TAXONOMY["duplicate_settlement"].expected_decision)

  def test_refund_clean_auto_closes(self):
    p = payment(amount_refunded=10000_00)
    run = reconcile([p], [line(10000_00, type_="refund", payment_id="pay_1")])
    d = decision_for("order_1", run)
    self.assertEqual(d.decision, TAXONOMY["refund_clean"].expected_decision)

  def test_refund_mismatch_escalates(self):
    p = payment(amount_refunded=10000_00)
    run = reconcile([p], [line(9500_00, type_="refund", payment_id="pay_1")])
    d = decision_for("order_1", run)
    self.assertEqual(d.decision, TAXONOMY["refund_mismatch"].expected_decision)

  def test_disputed_always_escalates_even_with_exact_amount_match(self):
    p = payment(dispute_id="disp_1")
    run = reconcile([p], [line(p.net_expected())])
    d = decision_for("order_1", run)
    self.assertEqual(d.decision, TAXONOMY["disputed"].expected_decision)
    self.assertEqual(d.reason_category, "disputed")

  def test_high_value_gate_escalates_even_with_exact_amount_match(self):
    p = payment(amount=60_000_00, fee=1200_00, tax=216_00)
    run = reconcile([p], [line(p.net_expected())])
    d = decision_for("order_1", run)
    self.assertEqual(d.decision, TAXONOMY["high_value_gate"].expected_decision)

  def test_international_fx_escalates_but_reason_is_generic_mismatch(self):
    p = payment(amount=5000_00, fee=100_00, tax=18_00)
    fx_settled = p.net_expected() - 700_00  # ~15% off, simulating FX conversion
    run = reconcile([p], [line(fx_settled)])
    d = decision_for("order_1", run)
    self.assertEqual(d.decision, TAXONOMY["international_fx"].expected_decision)
    self.assertEqual(d.reason_category, TAXONOMY["international_fx"].expected_reason_category)

  def test_quarantine_isolates_malformed_record_without_crashing(self):
    p = payment(order_id="")  # missing order_id, per taxonomy description
    run = reconcile([p], [])
    d = decision_for("pay_1", run)
    self.assertEqual(d.decision, TAXONOMY["quarantine"].expected_decision)

  def test_quarantine_negative_amount(self):
    p = payment(amount=-500_00)
    run = reconcile([p], [])
    d = decision_for("pay_1", run)
    self.assertEqual(d.decision, "quarantine")

  def test_engine_never_crashes_on_a_batch_of_every_case_type(self):
    payments = [
      payment(id_="pay_clean", order_id="order_clean"),
      payment(id_="pay_bad", order_id="", amount="not-a-number"),
    ]
    lines = [line(payments[0].net_expected(), order_id="order_clean")]
    run = reconcile(payments, lines)  # must not raise
    self.assertEqual(len(run.decisions), 2)


class TestBooksLeg(unittest.TestCase):
  """invoices=None (the default reconcile() signature, used by every test
  above) skips the books pass entirely. These tests explicitly pass an
  invoices list to enable it -- that's the whole 3-way loop."""

  def test_reconcile_without_invoices_arg_is_unaffected_by_books(self):
    p = payment()
    run = reconcile([p], [line(p.net_expected())])  # no invoices arg at all
    d = decision_for("order_1", run)
    self.assertEqual(d.reason_category, "clean_match")  # not books_clean_match

  def test_books_clean_match_ties_to_single_open_invoice(self):
    p = payment(amount=8000_00, fee=160_00, tax=29_00, customer_id="cust_A")
    run = reconcile([p], [line(p.net_expected())],
                     [invoice("inv_1", customer_id="cust_A", amount=8000_00)])
    d = decision_for("order_1", run)
    self.assertEqual(d.decision, TAXONOMY["books_clean_match"].expected_decision)
    self.assertEqual(d.reason_category, "books_clean_match")

  def test_books_duplicate_invoice_collision_abstains_rather_than_guesses(self):
    p = payment(amount=5000_00, fee=100_00, tax=18_00, customer_id="cust_B")
    invoices = [
      invoice("inv_1", customer_id="cust_B", amount=5000_00),
      invoice("inv_2", customer_id="cust_B", amount=5000_00),
    ]
    run = reconcile([p], [line(p.net_expected())], invoices)
    d = decision_for("order_1", run)
    self.assertEqual(d.decision,
                      TAXONOMY["books_duplicate_invoice_collision"].expected_decision)
    self.assertEqual(d.reason_category, "books_duplicate_invoice_collision")

  def test_books_missing_invoice_escalates_even_though_gateway_is_clean(self):
    p = payment(customer_id="cust_C")
    run = reconcile([p], [line(p.net_expected())], [])  # no invoice at all
    d = decision_for("order_1", run)
    self.assertEqual(d.decision, TAXONOMY["books_missing_invoice"].expected_decision)

  def test_books_amount_mismatch_escalates(self):
    p = payment(amount=6000_00, fee=120_00, tax=22_00, customer_id="cust_D")
    invoices = [invoice("inv_1", customer_id="cust_D", amount=5500_00)]
    run = reconcile([p], [line(p.net_expected())], invoices)
    d = decision_for("order_1", run)
    self.assertEqual(d.decision, TAXONOMY["books_amount_mismatch"].expected_decision)

  def test_no_invoice_double_consumed_invariant_holds(self):
    p = payment(customer_id="cust_A")
    run = reconcile([p], [line(p.net_expected())],
                     [invoice("inv_1", customer_id="cust_A")])
    self.assertTrue(run.invariants["no_invoice_double_consumed"])


class TestInvariants(unittest.TestCase):
  def test_invariants_hold_on_a_clean_batch(self):
    p1 = payment(id_="pay_1", order_id="order_1")
    p2 = payment(id_="pay_2", order_id="order_2")
    run = reconcile([p1, p2], [
      line(p1.net_expected(), order_id="order_1", entity_id="r1"),
      line(p2.net_expected(), order_id="order_2", entity_id="r2"),
    ])
    self.assertTrue(all(run.invariants.values()), run.invariants)

  def test_no_duplicate_decisions_for_same_case(self):
    p = payment()
    run = reconcile([p], [line(p.net_expected())])
    case_ids = [d.case_id for d in run.decisions]
    self.assertEqual(len(case_ids), len(set(case_ids)))


if __name__ == "__main__":
  unittest.main()
