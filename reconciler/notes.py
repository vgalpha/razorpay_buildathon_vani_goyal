"""Human-readable explanations for decided cases.

Template-based by default -- always works, no network dependency, and every
fact in the template came from engine.py's Decision, never invented here. If
ANTHROPIC_API_KEY or OPENAI_API_KEY is set in the environment, the template
sentence is optionally rephrased through that model for smoother prose. Any
failure on that path (no key, network error, timeout, bad response) falls
back to the template silently and correctly -- the LLM can only rephrase an
already-true sentence, never add a fact or change a decision.
"""

import json
import os
import urllib.error
import urllib.request

from .engine import Decision

_LLM_TIMEOUT_SECONDS = 8

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


def _call_anthropic(fact_sentence: str, api_key: str) -> str:
  body = json.dumps({
    "model": "claude-haiku-4-5-20251001",
    "max_tokens": 150,
    "messages": [{"role": "user", "content": (
      "Rephrase this reconciliation-system message for a finance-ops "
      "reviewer. Keep every number and fact exactly as given -- do not add, "
      "remove, or guess any fact. One or two plain sentences, no preamble:\n\n"
      f"{fact_sentence}")}],
  }).encode()
  req = urllib.request.Request(
    "https://api.anthropic.com/v1/messages", data=body, method="POST",
    headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
             "content-type": "application/json"})
  with urllib.request.urlopen(req, timeout=_LLM_TIMEOUT_SECONDS) as resp:
    parsed = json.loads(resp.read())
  return parsed["content"][0]["text"].strip()


def _call_openai(fact_sentence: str, api_key: str) -> str:
  body = json.dumps({
    "model": "gpt-4o-mini",
    "max_tokens": 150,
    "messages": [{"role": "user", "content": (
      "Rephrase this reconciliation-system message for a finance-ops "
      "reviewer. Keep every number and fact exactly as given -- do not add, "
      "remove, or guess any fact. One or two plain sentences, no preamble:\n\n"
      f"{fact_sentence}")}],
  }).encode()
  req = urllib.request.Request(
    "https://api.openai.com/v1/chat/completions", data=body, method="POST",
    headers={"Authorization": f"Bearer {api_key}",
             "content-type": "application/json"})
  with urllib.request.urlopen(req, timeout=_LLM_TIMEOUT_SECONDS) as resp:
    parsed = json.loads(resp.read())
  return parsed["choices"][0]["message"]["content"].strip()


def rephrase(fact_sentence: str) -> str:
  """Best-effort LLM rephrase of an already-fully-determined sentence. Falls
  back to the sentence unchanged on any missing key or failure -- this
  function can never fail the caller, only degrade to the template."""
  anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
  openai_key = os.environ.get("OPENAI_API_KEY")
  if not anthropic_key and not openai_key:
    return fact_sentence
  try:
    if anthropic_key:
      return _call_anthropic(fact_sentence, anthropic_key)
    return _call_openai(fact_sentence, openai_key)
  except Exception:
    return fact_sentence


def generate_note(decision: Decision) -> str:
  """The public entry point: a plain-English explanation for one decided
  case. Every fact in it came from `decision` (i.e. from engine.py's
  deterministic logic) -- this function only ever phrases, never decides."""
  return rephrase(_template_sentence(decision))
