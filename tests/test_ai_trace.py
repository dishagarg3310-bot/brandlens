"""'What the AI saw': the panel must show exactly what was sent, with personal data protected."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from streamlit.testing.v1 import AppTest

from app import seed
from app.core import llm
from app.db import database as db

EMAIL = "disha.private@example.com"
DRAFT = "Our cream is 100%% natural. Write to %s or call 98765 43210 for a sample." % EMAIL
APP = str(Path(__file__).resolve().parents[1] / "streamlit_app.py")

AI_ANSWER = json.dumps([
    {"category": "Tone", "severity": "low", "text": "Write to", "message": "Slightly abrupt.",
     "suggestion": "Feel free to write to", "rule_id": "G1", "fact_id": None, "confidence": "high"},
    {"category": "Tone", "severity": "low", "text": "words that are not in the draft", "message": "m",
     "suggestion": "s", "rule_id": "G1", "fact_id": None, "confidence": "high"},
])


class Trace(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        p = mock.patch.object(db, "DB_PATH", Path(tmp.name) / "t.db")
        p.start()
        self.addCleanup(p.stop)
        db.init_db()
        seed.seed_demo()
        self.sent = []

    def _run(self, ai_on=True, answer=AI_ANSWER, fail=False, use_checkbox=True):
        def fake_complete(system, prompt):
            self.sent.append(prompt)
            if fail:
                raise TimeoutError("slow")
            return answer
        patches = [mock.patch.object(llm, "provider", (lambda: "gemini") if ai_on else (lambda: None)),
                   mock.patch.object(llm, "_complete", fake_complete)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        at = AppTest.from_file(APP, default_timeout=60).run()
        [b for b in at.button if "Creator" in b.label][0].click().run()
        if ai_on and not use_checkbox:
            at.checkbox(key="use_ai").set_value(False).run()
        at.text_area(key="draft_text").set_value(DRAFT)
        [b for b in at.button if b.label == "Run review"][0].click().run()
        self.assertEqual(len(at.exception), 0)
        return at

    def _panel_text(self, at):
        parts = [m.value for m in at.markdown] + [c.value for c in at.code] + [c.value for c in at.success] \
            + [c.value for c in at.warning] + [c.value for c in at.info] + [c.value for c in at.caption]
        return "\n".join(parts)

    def test_personal_data_never_reaches_the_ai_and_the_panel_shows_what_was_sent(self):
        at = self._run()
        self.assertTrue(self.sent, "the AI should have been called")
        self.assertNotIn(EMAIL, self.sent[0])
        self.assertNotIn("98765 43210", self.sent[0])
        self.assertIn("[EMAIL_1]", self.sent[0])
        sent_box = "\n".join(c.value for c in at.code)      # the box titled "The text that was sent"
        self.assertIn("[EMAIL_1]", sent_box)
        self.assertIn("[PHONE_1]", sent_box)
        self.assertNotIn(EMAIL, sent_box)
        self.assertNotIn("98765", sent_box)
        text = self._panel_text(at)
        self.assertIn("1 email address", text)
        self.assertIn("1 phone number", text)

    def test_panel_lists_passages_and_counts_what_came_back(self):
        text = self._panel_text(self._run())
        self.assertIn("Guideline passages the AI was allowed to use", text)
        self.assertIn("2 suggestions", text)          # the AI returned two
        self.assertIn("1 passed our checks", text)    # one quoted words that are not in the draft

    def test_the_trace_is_saved_with_the_version(self):
        self._run()
        latest = max(db.list_drafts(), key=lambda d: d["id"])
        trace = db.get_ai_trace(db.latest_version(latest["id"])["id"])
        self.assertEqual(trace["status"], "ok")
        self.assertIn("[EMAIL_1]", trace["sent_text"])
        self.assertEqual(trace["redactions"]["EMAIL"], 1)

    def test_when_ai_is_off_the_panel_says_nothing_was_sent(self):
        at = self._run(ai_on=False)
        self.assertEqual(self.sent, [])
        self.assertIn("No outside service was called", self._panel_text(at))

    def test_when_the_ai_checkbox_is_off_nothing_is_sent(self):
        at = self._run(use_checkbox=False)
        self.assertEqual(self.sent, [])
        self.assertIn("switched off", self._panel_text(at))

    def test_when_the_ai_fails_the_panel_says_so_and_still_shows_what_was_sent(self):
        at = self._run(fail=True)
        text = self._panel_text(at)
        self.assertIn("did not answer in time", text)
        self.assertIn("[EMAIL_1]", text)


if __name__ == "__main__":
    unittest.main()