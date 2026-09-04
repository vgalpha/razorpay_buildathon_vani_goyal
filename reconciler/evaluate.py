"""Scores a ReconciliationRun against taxonomy-sourced ground truth.

Ground truth here always comes from generate.py's GroundTruthCase list,
which is itself sourced from taxonomy.py (see docs/ARCHITECTURE.md). This
file never invents its own idea of "correct".
"""

from dataclasses import dataclass, field
from typing import Dict, List

from .engine import Decision, ReconciliationRun
from .schema import GroundTruthCase


@dataclass
class EvalReport:
  total_cases: int
  overall_accuracy: float
  false_auto_close_rate: float
  auto_close_precision: float
  auto_close_recall: float
  auto_close_f1: float
  throughput_per_sec: float
  wall_time_seconds: float
  per_fault_class: Dict[str, Dict[str, float]] = field(default_factory=dict)
  per_rule: Dict[str, Dict[str, float]] = field(default_factory=dict)


def _safe_div(numerator, denominator):
  return numerator / denominator if denominator else 0.0


def evaluate(run: ReconciliationRun, ground_truth: List[GroundTruthCase]) -> EvalReport:
  gt_by_case = {gt.case_id: gt for gt in ground_truth}
  decisions_by_case = {d.case_id: d for d in run.decisions}

  tp = fp = fn = tn = correct = 0
  per_class: Dict[str, List[int]] = {}  # fault_type -> [correct, total]

  for case_id, gt in gt_by_case.items():
    decision = decisions_by_case.get(case_id)
    got = decision.decision if decision else "missing"
    is_correct = got == gt.expected_decision
    correct += int(is_correct)

    bucket = per_class.setdefault(gt.fault_type, [0, 0])
    bucket[1] += 1
    bucket[0] += int(is_correct)

    expected_auto = gt.expected_decision == "auto_close"
    got_auto = got == "auto_close"
    tp += int(expected_auto and got_auto)
    fp += int(got_auto and not expected_auto)
    fn += int(expected_auto and not got_auto)
    tn += int(not expected_auto and not got_auto)

  precision = _safe_div(tp, tp + fp)
  recall = _safe_div(tp, tp + fn)
  f1 = _safe_div(2 * precision * recall, precision + recall)
  total = len(gt_by_case)

  per_rule: Dict[str, List[int]] = {}
  for d in run.decisions:
    gt = gt_by_case.get(d.case_id)
    bucket = per_rule.setdefault(d.rule, [0, 0])
    bucket[1] += 1
    bucket[0] += int(gt is not None and gt.expected_decision == d.decision)

  return EvalReport(
    total_cases=total,
    overall_accuracy=_safe_div(correct, total),
    false_auto_close_rate=_safe_div(fp, total),
    auto_close_precision=precision,
    auto_close_recall=recall,
    auto_close_f1=f1,
    throughput_per_sec=_safe_div(total, run.wall_time_seconds),
    wall_time_seconds=run.wall_time_seconds,
    per_fault_class={k: {"correct": v[0], "total": v[1], "accuracy": _safe_div(v[0], v[1])}
                      for k, v in sorted(per_class.items())},
    per_rule={k: {"correct": v[0], "total": v[1], "accuracy": _safe_div(v[0], v[1])}
              for k, v in sorted(per_rule.items())},
  )
