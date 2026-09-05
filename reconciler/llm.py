"""Pluggable LLM client -- one place that knows how to reach any of a few
popular providers, so the rest of the codebase (notes.py, qa.py) never has
to know which one is configured.

Provider selection: LLM_PROVIDER ("anthropic" | "openai" | "gemini" |
"openai_compatible") if set, otherwise auto-detected from whichever API key
is present (checked in that order) -- this preserves the original
zero-config behavior where just setting ANTHROPIC_API_KEY or OPENAI_API_KEY
was enough. "openai_compatible" covers any provider that speaks the OpenAI
chat-completions wire format (Groq, Together, OpenRouter, a local Ollama,
etc.) via LLM_BASE_URL + LLM_API_KEY + LLM_MODEL, without a dedicated
adapter per provider.

Every caller in this codebase must keep to the rule enforced by notes.py and
qa.py, not by this module: the LLM may only phrase or summarize facts it is
explicitly given, never decide anything or invent a fact. This module just
makes the network call and raises on failure -- callers are responsible for
falling back to a deterministic answer.
"""

import json
import os
import urllib.request

_TIMEOUT_SECONDS = 8

_DEFAULT_MODELS = {
  "anthropic": "claude-haiku-4-5-20251001",
  "openai": "gpt-4o-mini",
  "gemini": "gemini-2.0-flash",
}


def _call_anthropic(prompt: str, api_key: str, model: str) -> str:
  body = json.dumps({
    "model": model, "max_tokens": 300,
    "messages": [{"role": "user", "content": prompt}],
  }).encode()
  req = urllib.request.Request(
    "https://api.anthropic.com/v1/messages", data=body, method="POST",
    headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
             "content-type": "application/json"})
  with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
    parsed = json.loads(resp.read())
  return parsed["content"][0]["text"].strip()


def _call_openai_style(prompt: str, api_key: str, model: str, base_url: str) -> str:
  """OpenAI's chat-completions wire format -- also used for any
  "openai_compatible" provider, since Groq/Together/OpenRouter/Ollama all
  implement the same request/response shape."""
  body = json.dumps({
    "model": model, "max_tokens": 300,
    "messages": [{"role": "user", "content": prompt}],
  }).encode()
  headers = {"content-type": "application/json"}
  if api_key:
    headers["Authorization"] = f"Bearer {api_key}"
  req = urllib.request.Request(
    f"{base_url.rstrip('/')}/chat/completions", data=body, method="POST",
    headers=headers)
  with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
    parsed = json.loads(resp.read())
  return parsed["choices"][0]["message"]["content"].strip()


def _call_gemini(prompt: str, api_key: str, model: str) -> str:
  body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
  url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
         f"{model}:generateContent?key={api_key}")
  req = urllib.request.Request(url, data=body, method="POST",
                                headers={"content-type": "application/json"})
  with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
    parsed = json.loads(resp.read())
  return parsed["candidates"][0]["content"]["parts"][0]["text"].strip()


def _resolve_provider() -> str:
  provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
  if provider:
    return provider
  if os.environ.get("ANTHROPIC_API_KEY"):
    return "anthropic"
  if os.environ.get("OPENAI_API_KEY"):
    return "openai"
  if os.environ.get("GEMINI_API_KEY"):
    return "gemini"
  return ""


def is_configured() -> bool:
  return bool(_resolve_provider())


def active_provider() -> str:
  """The resolved provider name, or "" if none is configured -- purely
  informational (e.g. for a status endpoint or docs), never used to decide
  reconciliation logic."""
  return _resolve_provider()


def call_llm(prompt: str) -> str:
  """Raises on any failure (missing config, network, bad response) --
  callers must catch and fall back to a deterministic answer."""
  provider = _resolve_provider()
  model = os.environ.get("LLM_MODEL") or _DEFAULT_MODELS.get(provider)
  if provider == "anthropic":
    return _call_anthropic(prompt, os.environ["ANTHROPIC_API_KEY"], model)
  if provider == "openai":
    return _call_openai_style(prompt, os.environ["OPENAI_API_KEY"], model,
                               "https://api.openai.com/v1")
  if provider == "gemini":
    return _call_gemini(prompt, os.environ["GEMINI_API_KEY"], model)
  if provider == "openai_compatible":
    base_url = os.environ.get("LLM_BASE_URL")
    if not base_url:
      raise ValueError("LLM_BASE_URL is required for LLM_PROVIDER=openai_compatible")
    if not model:
      raise ValueError("LLM_MODEL is required for LLM_PROVIDER=openai_compatible")
    return _call_openai_style(prompt, os.environ.get("LLM_API_KEY", ""), model, base_url)
  raise ValueError(f"no LLM provider configured (LLM_PROVIDER={provider!r})")
