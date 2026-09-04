"""CLI entrypoint: generate -> reconcile -> evaluate -> render report.

Usage: python3 run.py
"""

import os

from reconciler import qa
from reconciler.engine import reconcile
from reconciler.evaluate import evaluate
from reconciler.generate import generate_dataset
from reconciler.report import render

OUT_DIR = os.path.join(os.path.dirname(__file__), "out")

_DEMO_QUESTIONS = [
  "what's the match rate?",
  "what broke?",
  "how fast was the run?",
  "what's the biggest exception?",
  "what do you refuse to guess on?",
]


def _print_qa_demo(run, ev, payments):
  print("\n--- Q&A demo (canned questions, deterministic-computed answers) ---")
  for q in _DEMO_QUESTIONS:
    print(f"Q: {q}")
    print(f"A: {qa.answer(q, run, ev, payments)}\n")


def main():
  dataset = generate_dataset()
  run = reconcile(dataset.payments, dataset.settlement_lines, dataset.invoices)
  ev = evaluate(run, dataset.ground_truth)

  os.makedirs(OUT_DIR, exist_ok=True)
  report_path = os.path.join(OUT_DIR, "report.html")
  with open(report_path, "w") as f:
    f.write(render(dataset, run, ev))

  print(f"Cases: {ev.total_cases}")
  print(f"Overall accuracy: {ev.overall_accuracy*100:.1f}%")
  print(f"False auto-close rate: {ev.false_auto_close_rate*100:.2f}%")
  print(f"Auto-close precision/recall/F1: "
        f"{ev.auto_close_precision*100:.1f}% / {ev.auto_close_recall*100:.1f}% / "
        f"{ev.auto_close_f1*100:.1f}%")
  print(f"Throughput: {ev.throughput_per_sec:,.0f} records/sec "
        f"({ev.wall_time_seconds*1000:.2f} ms wall time)")
  print(f"Invariants: {run.invariants}")
  print(f"Report written to {report_path}")
  _print_qa_demo(run, ev, dataset.payments)


if __name__ == "__main__":
  main()
