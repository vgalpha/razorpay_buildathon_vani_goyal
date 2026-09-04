"""Renders a single static HTML report from a run's results.

No server, no client-side reimplementation of any logic -- every number on
the page was computed in Python and is just being printed here.
"""

import html
from typing import Dict, List

from .engine import Decision, ReconciliationRun
from .evaluate import EvalReport
from .generate import Dataset
from .notes import generate_note
from .taxonomy import TAXONOMY

_STATUS_CLASS = {"auto_close": "ok", "escalate": "warn", "quarantine": "bad"}
_STATUS_LABEL = {"auto_close": "AUTO-CLOSED", "escalate": "ESCALATED", "quarantine": "QUARANTINED"}

_LIMITATION_TEXT = (
  "This engine has no FX-conversion model. International payments settled "
  "in INR after currency conversion are always correctly escalated for "
  "human review (it never mis-closes one), but it can only label the cause "
  "as a generic 'amount mismatch' -- it cannot yet tell you the difference "
  "is FX conversion rather than an error. That distinction is not built."
)


def _esc(s) -> str:
  return html.escape(str(s))


def _metric_card(label: str, value: str) -> str:
  return f'<div class="card"><div class="card-label">{_esc(label)}</div>' \
         f'<div class="card-value">{_esc(value)}</div></div>'


def _fault_table(per_fault_class: Dict[str, Dict[str, float]]) -> str:
  rows = []
  for fault_type, stats in per_fault_class.items():
    spec = TAXONOMY.get(fault_type)
    expected = spec.expected_decision if spec else "?"
    rows.append(
      f'<tr><td>{_esc(fault_type)}</td><td>{_esc(expected)}</td>'
      f'<td>{stats["correct"]}/{stats["total"]}</td>'
      f'<td>{stats["accuracy"]*100:.1f}%</td></tr>')
  return (
    '<table><thead><tr><th>Fault class</th><th>Expected decision</th>'
    '<th>Correct / total</th><th>Accuracy</th></tr></thead>'
    f'<tbody>{"".join(rows)}</tbody></table>')


def _rule_table(per_rule: Dict[str, Dict[str, float]]) -> str:
  rows = []
  for rule, stats in per_rule.items():
    rows.append(
      f'<tr><td>{_esc(rule)}</td><td>{stats["total"]}</td>'
      f'<td>{stats["correct"]}/{stats["total"]}</td></tr>')
  return (
    '<table><thead><tr><th>Rule</th><th>Fired</th><th>Correct / total</th>'
    '</tr></thead>'
    f'<tbody>{"".join(rows)}</tbody></table>')


def _invariants_panel(invariants: Dict[str, bool]) -> str:
  items = []
  for name, ok in invariants.items():
    cls = "ok" if ok else "bad"
    label = "HOLDS" if ok else "VIOLATED"
    items.append(f'<div class="invariant {cls}">{_esc(name)}: <b>{label}</b></div>')
  return "".join(items)


def _exceptions_section(decisions: List[Decision]) -> str:
  escalated = [d for d in decisions if d.decision == "escalate"]
  by_category: Dict[str, List[Decision]] = {}
  for d in escalated:
    by_category.setdefault(d.reason_category, []).append(d)
  blocks = []
  for category, items in sorted(by_category.items()):
    rows = "".join(
      f'<tr><td class="mono">{_esc(d.case_id)}</td><td>{_esc(generate_note(d))}</td>'
      f'<td class="mono">{_esc(", ".join(d.record_ids))}</td></tr>' for d in items)
    blocks.append(
      f'<h3>{_esc(category)} <span class="count">({len(items)})</span></h3>'
      f'<table><thead><tr><th>Case</th><th>Explanation</th><th>Records</th></tr></thead>'
      f'<tbody>{rows}</tbody></table>')
  return "".join(blocks) if blocks else "<p>No exceptions.</p>"


def _quarantine_section(decisions: List[Decision]) -> str:
  quarantined = [d for d in decisions if d.decision == "quarantine"]
  if not quarantined:
    return "<p>Nothing quarantined.</p>"
  rows = "".join(
    f'<tr><td class="mono">{_esc(d.case_id)}</td><td>{_esc(d.reason_detail)}</td></tr>'
    for d in quarantined)
  return (f'<table><thead><tr><th>Record</th><th>Reason isolated</th></tr></thead>'
          f'<tbody>{rows}</tbody></table>')


def _record_table(decisions: List[Decision]) -> str:
  rows = []
  for d in decisions:
    cls = _STATUS_CLASS[d.decision]
    label = _STATUS_LABEL[d.decision]
    rows.append(
      f'<tr class="{cls}"><td class="mono">{_esc(d.case_id)}</td>'
      f'<td><span class="pill {cls}">{label}</span></td>'
      f'<td>{_esc(d.reason_category)}</td><td>{_esc(d.reason_detail)}</td>'
      f'<td>{_esc(d.rule)}</td></tr>')
  return (
    '<table><thead><tr><th>Case</th><th>Status</th><th>Reason</th>'
    '<th>Detail</th><th>Rule</th></tr></thead>'
    f'<tbody>{"".join(rows)}</tbody></table>')


_STYLE = """
:root { color-scheme: dark; }
body { background:#0b0d10; color:#e6e6e6; font-family:-apple-system,Segoe UI,sans-serif; margin:0; padding:32px; }
h1 { font-size:28px; margin:0 0 4px; }
h2 { margin-top:40px; border-bottom:1px solid #262a30; padding-bottom:8px; }
h3 { margin-top:24px; color:#9fb3c8; }
.subtitle { color:#8a94a3; margin-bottom:24px; }
.mono { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:13px; }
.cards { display:flex; flex-wrap:wrap; gap:16px; }
.card { background:#14171c; border:1px solid #262a30; border-radius:10px; padding:16px 20px; min-width:150px; }
.card-label { color:#8a94a3; font-size:12px; text-transform:uppercase; letter-spacing:.05em; }
.card-value { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:26px; margin-top:6px; }
table { border-collapse:collapse; width:100%; margin-top:8px; }
th, td { text-align:left; padding:8px 10px; border-bottom:1px solid #1e2227; font-size:13px; }
th { color:#8a94a3; font-weight:600; }
.pill { padding:2px 8px; border-radius:999px; font-size:11px; font-weight:600; }
.pill.ok { background:#123524; color:#4ade80; }
.pill.warn { background:#3a2c12; color:#facc15; }
.pill.bad { background:#3a1414; color:#f87171; }
.invariant { padding:8px 12px; border-radius:8px; margin-bottom:6px; font-size:13px; }
.invariant.ok { background:#123524; color:#4ade80; }
.invariant.bad { background:#3a1414; color:#f87171; }
.limitations { background:#241c0d; border:1px solid #4a3b17; border-radius:10px; padding:16px 20px; color:#e8d5a0; }
.count { color:#8a94a3; font-weight:400; }
"""


def render(dataset: Dataset, run: ReconciliationRun, ev: EvalReport) -> str:
  auto = sum(1 for d in run.decisions if d.decision == "auto_close")
  esc = sum(1 for d in run.decisions if d.decision == "escalate")
  qtn = sum(1 for d in run.decisions if d.decision == "quarantine")
  cards = "".join([
    _metric_card("Total cases", str(ev.total_cases)),
    _metric_card("Auto-closed", f"{auto} ({auto/ev.total_cases*100:.0f}%)"),
    _metric_card("Escalated", f"{esc} ({esc/ev.total_cases*100:.0f}%)"),
    _metric_card("Quarantined", str(qtn)),
    _metric_card("False auto-close rate", f"{ev.false_auto_close_rate*100:.2f}%"),
    _metric_card("Throughput", f"{ev.throughput_per_sec:,.0f} rec/s"),
    _metric_card("Wall time", f"{ev.wall_time_seconds*1000:.2f} ms"),
  ])
  return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Reconciliation report</title><style>{_STYLE}</style></head><body>
<h1>Settlement reconciliation report</h1>
<div class="subtitle">Payments &harr; settlement recon &harr; books, 3-source loop. One cherry-picked match proves nothing -- this is the full batch.</div>
<div class="cards">{cards}</div>

<h2>Invariants</h2>
{_invariants_panel(run.invariants)}

<h2>Accuracy by fault class</h2>
{_fault_table(ev.per_fault_class)}

<h2>Per-rule scorecard</h2>
{_rule_table(ev.per_rule)}

<h2>Known limitation (disclosed, not hidden)</h2>
<div class="limitations">{_esc(_LIMITATION_TEXT)}</div>

<h2>Exceptions ({sum(1 for d in run.decisions if d.decision == "escalate")})</h2>
{_exceptions_section(run.decisions)}

<h2>Quarantined records ({sum(1 for d in run.decisions if d.decision == "quarantine")})</h2>
{_quarantine_section(run.decisions)}

<h2>All cases</h2>
{_record_table(run.decisions)}
</body></html>"""
