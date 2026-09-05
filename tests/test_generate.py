"""Generator tests. The default (no-args) path underpins the documented
seed-42/207-case verified benchmark cited in README.md -- it must never
change, so it gets an exact-value regression test rather than just a shape
check.
"""

import unittest
from collections import Counter

from reconciler.generate import generate_dataset, jitter_taxonomy_counts, \
  scale_taxonomy_counts
from reconciler.taxonomy import TAXONOMY


class TestDefaultPathIsUnchanged(unittest.TestCase):
  def test_default_call_matches_the_documented_benchmark_exactly(self):
    ds = generate_dataset()
    self.assertEqual(len(ds.ground_truth), 207)
    self.assertEqual(len(ds.payments), 222)
    self.assertEqual(len(ds.settlement_lines), 200)
    self.assertEqual(len(ds.invoices), 117)
    self.assertEqual(ds.payments[0].id, "pay_Ubzq0aVnLecBwS")
    self.assertEqual(ds.payments[-1].id, "pay_k77u5yXroUqQE8")
    self.assertEqual(ds.settlement_lines[0].entity_id, "recon_IAoCLrZ3aWZkSB")
    self.assertEqual(ds.invoices[0].id, "inv_fJs1ON43xKmTec")

  def test_default_call_is_deterministic_across_repeated_calls(self):
    a = generate_dataset()
    b = generate_dataset()
    self.assertEqual([p.id for p in a.payments], [p.id for p in b.payments])


class TestFaultCountsOverride(unittest.TestCase):
  def test_explicit_counts_are_respected_exactly(self):
    counts = {ft: 0 for ft in TAXONOMY}
    counts["clean_match"] = 3
    counts["disputed"] = 2
    ds = generate_dataset(seed=7, fault_counts=counts)
    by_type = Counter(gt.fault_type for gt in ds.ground_truth)
    self.assertEqual(by_type["clean_match"], 3)
    self.assertEqual(by_type["disputed"], 2)
    self.assertEqual(sum(by_type.values()), 5)

  def test_missing_keys_fall_back_to_taxonomy_defaults(self):
    ds = generate_dataset(seed=7, fault_counts={"clean_match": 1})
    by_type = Counter(gt.fault_type for gt in ds.ground_truth)
    self.assertEqual(by_type["clean_match"], 1)
    self.assertEqual(by_type["disputed"], TAXONOMY["disputed"].count)

  def test_same_seed_and_counts_is_deterministic(self):
    counts = {"clean_match": 5}
    a = generate_dataset(seed=3, fault_counts=counts)
    b = generate_dataset(seed=3, fault_counts=counts)
    self.assertEqual([p.id for p in a.payments], [p.id for p in b.payments])


class TestJitterTaxonomyCounts(unittest.TestCase):
  def test_never_goes_below_the_default(self):
    counts = jitter_taxonomy_counts(seed=1)
    for ft, spec in TAXONOMY.items():
      self.assertGreaterEqual(counts[ft], spec.count)

  def test_stays_within_the_spread_ceiling(self):
    counts = jitter_taxonomy_counts(seed=1, spread=0.3)
    for ft, spec in TAXONOMY.items():
      self.assertLessEqual(counts[ft], round(spec.count * 1.3))

  def test_same_seed_is_deterministic(self):
    self.assertEqual(jitter_taxonomy_counts(seed=99), jitter_taxonomy_counts(seed=99))

  def test_covers_every_taxonomy_fault_type(self):
    self.assertEqual(set(jitter_taxonomy_counts(seed=1)), set(TAXONOMY))


class TestScaleTaxonomyCounts(unittest.TestCase):
  def test_total_lands_close_to_the_requested_size(self):
    counts = scale_taxonomy_counts(1000)
    base_total = sum(spec.count for spec in TAXONOMY.values())
    self.assertAlmostEqual(sum(counts.values()), 1000, delta=len(TAXONOMY))
    self.assertGreater(sum(counts.values()), base_total)

  def test_every_class_keeps_at_least_one_case(self):
    counts = scale_taxonomy_counts(20)
    for ft in TAXONOMY:
      self.assertGreaterEqual(counts[ft], 1)

  def test_is_deterministic_no_randomness(self):
    self.assertEqual(scale_taxonomy_counts(500), scale_taxonomy_counts(500))


if __name__ == "__main__":
  unittest.main()
