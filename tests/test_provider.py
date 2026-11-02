import contextlib
import io
import json
import os
import unittest
from unittest import mock

from app.core import llm

KEYS = ("AI_PROVIDER", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GEMINI_MODEL")


@contextlib.contextmanager
def _env(**kw):
    clean = {k: v for k, v in os.environ.items() if k not in KEYS}
    clean.update(kw)
    # keys come only from this fake environment, never from .streamlit/secrets.toml
    with mock.patch.dict(os.environ, clean, clear=True), \
            mock.patch.object(llm, "_secret", lambda name: os.environ.get(name)):
        yield


class TestProvider(unittest.TestCase):
    def test_no_key_means_ai_off(self):
        with _env():
            self.assertIsNone(llm.provider())
            self.assertFalse(llm.ai_available())

    def test_gemini_only(self):
        with _env(GEMINI_API_KEY="g"):
            self.assertEqual(llm.provider(), "gemini")
            self.assertTrue(llm.ai_available())

    def test_anthropic_wins_when_both_unless_forced(self):
        with _env(GEMINI_API_KEY="g", ANTHROPIC_API_KEY="a"):
            self.assertEqual(llm.provider(), "anthropic")
        with _env(GEMINI_API_KEY="g", ANTHROPIC_API_KEY="a", AI_PROVIDER="gemini"):
            self.assertEqual(llm.provider(), "gemini")

    def test_forced_provider_without_key_falls_back(self):
        with _env(GEMINI_API_KEY="g", AI_PROVIDER="anthropic"):
            self.assertEqual(llm.provider(), "gemini")


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TestGeminiCall(unittest.TestCase):
    def test_request_shape_and_text_extraction(self):
        payload = {"candidates": [{"content": {"parts": [{"text": "[]"}]}}]}
        seen = {}

        def fake_urlopen(req, timeout=0):
            seen["url"] = req.full_url
            seen["headers"] = {k.lower(): v for k, v in req.header_items()}
            seen["body"] = json.loads(req.data.decode("utf-8"))
            return _FakeResponse(json.dumps(payload).encode("utf-8"))

        with _env(GEMINI_API_KEY="secret-key"), mock.patch("urllib.request.urlopen", fake_urlopen):
            out = llm._call_gemini("SYS", "PROMPT")
        self.assertEqual(out, "[]")
        self.assertIn(llm.DEFAULT_GEMINI_MODEL + ":generateContent", seen["url"])
        self.assertNotIn("secret-key", seen["url"])  # key travels in a header, not the URL
        self.assertEqual(seen["headers"]["x-goog-api-key"], "secret-key")
        self.assertEqual(seen["body"]["contents"][0]["parts"][0]["text"], "PROMPT")
        self.assertEqual(seen["body"]["system_instruction"]["parts"][0]["text"], "SYS")

    def test_blocked_or_empty_response_returns_empty_text(self):
        with _env(GEMINI_API_KEY="k"), mock.patch(
            "urllib.request.urlopen", lambda req, timeout=0: _FakeResponse(b"{}")
        ):
            self.assertEqual(llm._call_gemini("S", "P"), "")


if __name__ == "__main__":
    unittest.main()
