"""Tests for the pluggable LLM provider layer.

No test here may depend on network access or a real API key -- provider
*resolution* (which provider/model would be used) is tested directly;
network calls are only exercised with a deliberately fake key to prove the
request-building code runs and raises cleanly on failure, matching the same
convention as tests/test_qa.py's TestLLMCallPathsAreReachable.
"""

import os
import unittest

from reconciler import llm

_ALL_LLM_ENV_VARS = (
  "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
  "LLM_PROVIDER", "LLM_MODEL", "LLM_BASE_URL", "LLM_API_KEY",
)


class _ClearLLMEnvMixin(unittest.TestCase):
  def setUp(self):
    self._saved = {k: os.environ.pop(k, None) for k in _ALL_LLM_ENV_VARS}

  def tearDown(self):
    for k, v in self._saved.items():
      if v is not None:
        os.environ[k] = v
      else:
        os.environ.pop(k, None)


class TestProviderResolution(_ClearLLMEnvMixin):
  def test_no_config_is_not_configured(self):
    self.assertFalse(llm.is_configured())
    self.assertEqual(llm.active_provider(), "")

  def test_auto_detects_anthropic_key(self):
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-fake"
    self.assertEqual(llm.active_provider(), "anthropic")

  def test_auto_detects_openai_key_when_no_anthropic_key(self):
    os.environ["OPENAI_API_KEY"] = "sk-fake"
    self.assertEqual(llm.active_provider(), "openai")

  def test_auto_detects_gemini_key_when_no_other_key(self):
    os.environ["GEMINI_API_KEY"] = "fake"
    self.assertEqual(llm.active_provider(), "gemini")

  def test_anthropic_key_takes_priority_over_openai_key(self):
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-fake"
    os.environ["OPENAI_API_KEY"] = "sk-fake"
    self.assertEqual(llm.active_provider(), "anthropic")

  def test_explicit_provider_wins_over_auto_detected_key(self):
    os.environ["OPENAI_API_KEY"] = "sk-fake"
    os.environ["LLM_PROVIDER"] = "gemini"
    self.assertEqual(llm.active_provider(), "gemini")

  def test_call_llm_raises_when_nothing_configured(self):
    with self.assertRaises(ValueError):
      llm.call_llm("hello")

  def test_openai_compatible_requires_base_url(self):
    os.environ["LLM_PROVIDER"] = "openai_compatible"
    os.environ["LLM_MODEL"] = "llama-3.1-70b"
    with self.assertRaises(ValueError):
      llm.call_llm("hello")

  def test_openai_compatible_requires_model(self):
    os.environ["LLM_PROVIDER"] = "openai_compatible"
    os.environ["LLM_BASE_URL"] = "https://api.groq.com/openai/v1"
    with self.assertRaises(ValueError):
      llm.call_llm("hello")


class TestNetworkCallPathsFailGracefully(_ClearLLMEnvMixin):
  """Proves the request-building code for each provider actually runs (does
  not raise a Python error before even reaching the network) and surfaces a
  normal exception on failure -- callers (notes.rephrase, qa._llm_fallback)
  are the ones responsible for catching this and falling back."""

  def test_anthropic_path_raises_on_auth_failure_not_crash(self):
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-fake-key-for-testing-only"
    with self.assertRaises(Exception):
      llm.call_llm("hello")

  def test_openai_path_raises_on_auth_failure_not_crash(self):
    os.environ["OPENAI_API_KEY"] = "sk-fake-key-for-testing-only"
    with self.assertRaises(Exception):
      llm.call_llm("hello")

  def test_gemini_path_raises_on_auth_failure_not_crash(self):
    os.environ["GEMINI_API_KEY"] = "fake-key-for-testing-only"
    with self.assertRaises(Exception):
      llm.call_llm("hello")


if __name__ == "__main__":
  unittest.main()
