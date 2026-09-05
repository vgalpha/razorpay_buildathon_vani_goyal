"""Human-readable explanations for decided cases.

Template-based by default -- always works, no network dependency, and every
fact in the template came from engine.py's Decision, never invented here. If
an LLM provider is configured (see llm.py -- any of ANTHROPIC_API_KEY,
OPENAI_API_KEY, GEMINI_API_KEY, or an explicit LLM_PROVIDER), the template
sentence is optionally rephrased through that model for smoother prose. Any
failure on that path (no key, network error, timeout, bad response) falls
back to the template silently and correctly -- the LLM can only rephrase an
already-true sentence, never add a fact or change a decision.
"""

from .engine import Decision
from .llm import call_llm, is_configured

_TEMPLATES = {
  "clean_match": "{detail} -- closed automatically.",
  "rounding_noise": "{detail} -- closed automatically.",
  "amount_mismatch": "{detail}. Escalated: the difference exceeds the "
                      "auto-close tolerance.",
  "multi_payment_ambiguous": "{detail}. Escalated -- this is a schema "
                              "limitation, not a confidence judgment, so it "
                              "cannot be resolved by trying harder.",
  "missing_settlement": "{detail}. Escalated: nothing to reconcile against yet.",
  "duplicate_settlement": "{detail}. Escalated: more than one settlement "
                           "line claims to cover this payment.",
  "refund_clean": "{detail} -- closed automatically.",
  "refund_mismatch": "{detail}. Escalated: the refunded settlement doesn't "
                      "match what was recorded as refunded.",
  "disputed": "{detail}.",
  "high_value_gate": "{detail}. Escalated regardless of match quality -- "
                      "this is a value-based control, not a sign something "
                      "is wrong.",
  "books_clean_match": "{detail} -- closed automatically.",
  "books_duplicate_invoice_collision": "{detail}.",
  "books_missing_invoice": "{detail}.",
  "books_amount_mismatch": "{detail}.",
  "quarantine": "{detail}. Isolated before any matching logic ran; the "
                "batch continued.",
}


def _template_sentence(decision: Decision) -> str:
  tmpl = _TEMPLATES.get(decision.reason_category, "{detail}")
  return tmpl.format(detail=decision.reason_detail)


def rephrase(fact_sentence: str) -> str:
  """Best-effort LLM rephrase of an already-fully-determined sentence. Falls
  back to the sentence unchanged on any missing key or failure -- this
  function can never fail the caller, only degrade to the template."""
  if not is_configured():
    return fact_sentence
  try:
    return call_llm(
      "Rephrase this reconciliation-system message for a finance-ops "
      "reviewer. Keep every number and fact exactly as given -- do not add, "
      "remove, or guess any fact. One or two plain sentences, no preamble:\n\n"
      f"{fact_sentence}")
  except Exception:
    return fact_sentence


def generate_note(decision: Decision) -> str:
  """The public entry point: a plain-English explanation for one decided
  case. Every fact in it came from `decision` (i.e. from engine.py's
  deterministic logic) -- this function only ever phrases, never decides."""
  return rephrase(_template_sentence(decision))
