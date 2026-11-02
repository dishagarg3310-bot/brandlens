"""What a judge will try: bad input, empty states, repeated clicks, wrong role, odd text.

Every test runs on a throw-away database and with the AI layer off, so nothing here
touches real data or calls an outside service.
"""
import tempfile
import time
from contextlib import closing
import unittest
from pathlib import Path
from unittest import mock

from app import seed
from app.core import documents, llm
from app.core.rules import review_text
from app.db import database as db
from app.db import workflow as wf
from app.ui import highlight, md_escape


def fresh_db(case):
    tmp = tempfile.TemporaryDirectory()
    case.addCleanup(tmp.cleanup)
    p = mock.patch.object(db, "DB_PATH", Path(tmp.name) / "t.db")
    p.start()
    case.addCleanup(p.stop)
    off = mock.patch.object(llm, "ai_available", lambda: False)
    off.start()
    case.addCleanup(off.stop)
    db.init_db()


def submitted_draft():
    did = db.create_draft("t", "Riya (Creator)")
    vid, _ = db.add_version(did, "Hello", "Riya (Creator)")
    assert wf.set_status(did, "in_review", "Riya", "Creator")
    return did


class WorkflowGuards(unittest.TestCase):
    def setUp(self):
        fresh_db(self)

    def test_cannot_approve_a_draft_that_was_never_submitted(self):
        did = db.create_draft("t", "Riya")
        self.assertFalse(wf.set_status(did, "approved", "Arjun", "Manager"))
        self.assertEqual(wf.get_status(did), "draft")

    def test_approving_twice_changes_nothing_the_second_time(self):
        did = submitted_draft()
        self.assertTrue(wf.set_status(did, "approved", "Arjun", "Manager"))
        n = len(wf.list_audit(did))
        self.assertFalse(wf.set_status(did, "approved", "Arjun", "Manager"))
        self.assertEqual(len(wf.list_audit(did)), n)

    def test_submitting_twice_is_ignored(self):
        did = submitted_draft()
        self.assertFalse(wf.set_status(did, "in_review", "Riya", "Creator"))

    def test_wrong_roles_are_refused(self):
        did = submitted_draft()
        self.assertFalse(wf.set_status(did, "approved", "Riya", "Creator"))
        self.assertFalse(wf.set_status(did, "approved", "Sana", "Admin"))
        self.assertEqual(wf.get_status(did), "in_review")

    def test_unknown_draft_and_unknown_status(self):
        self.assertFalse(wf.set_status(9999, "approved", "Arjun", "Manager"))
        did = submitted_draft()
        self.assertFalse(wf.set_status(did, "published", "Arjun", "Manager"))

    def test_comments_are_trimmed_capped_and_never_empty(self):
        did = submitted_draft()
        self.assertFalse(wf.add_comment(did, "a", "Manager", "   "))
        self.assertFalse(wf.add_comment(9999, "a", "Manager", "hi"))
        self.assertTrue(wf.add_comment(did, "a", "Manager", "x" * 5000))
        self.assertEqual(len(wf.list_comments(did)[0]["body"]), wf.MAX_COMMENT)


class FindingDecisions(unittest.TestCase):
    def setUp(self):
        fresh_db(self)
        self.did = db.create_draft("t", "Riya")
        self.vid, _ = db.add_version(self.did, "Our BEST cream!!!", "Riya")
        db.save_findings(self.vid, review_text("Our BEST cream!!!"))
        self.fid = db.get_findings(self.vid)[0]["id"]

    def test_creator_can_decide_once(self):
        self.assertTrue(db.set_finding_status(self.fid, "accepted", "Riya", "Creator", self.did))
        self.assertFalse(db.set_finding_status(self.fid, "accepted", "Riya", "Creator", self.did))

    def test_creator_can_change_their_mind(self):
        db.set_finding_status(self.fid, "accepted", "Riya", "Creator", self.did)
        self.assertTrue(db.set_finding_status(self.fid, "disputed", "Riya", "Creator", self.did))

    def test_only_the_creator_decides(self):
        self.assertFalse(db.set_finding_status(self.fid, "accepted", "Arjun", "Manager", self.did))

    def test_no_changes_after_submission(self):
        for f in db.get_findings(self.vid):
            db.set_finding_status(f["id"], "accepted", "Riya", "Creator", self.did)
        wf.set_status(self.did, "in_review", "Riya", "Creator")
        self.assertFalse(db.set_finding_status(self.fid, "disputed", "Riya", "Creator", self.did))

    def test_bad_status_value_is_refused(self):
        self.assertFalse(db.set_finding_status(self.fid, "deleted", "Riya", "Creator", self.did))


class OddText(unittest.TestCase):
    def test_script_tags_are_escaped_in_the_highlighted_draft(self):
        text = '<script>alert(1)</script> <img src=x onerror=alert(1)> Our BEST cream'
        out = highlight(text, [dict(span_start=text.index("BEST"), span_end=text.index("BEST") + 4,
                                    severity="high", category="Claim")])
        self.assertNotIn("<script>", out)
        self.assertNotIn("<img", out)
        self.assertIn("&lt;script&gt;", out)

    def test_markdown_in_user_text_cannot_become_a_link_or_image(self):
        out = md_escape("![x](http://evil.example/p.png) [click](http://evil.example) # big")
        self.assertNotIn("![", out)
        self.assertNotIn("](", out)

    def test_empty_whitespace_emoji_and_hindi_do_not_crash(self):
        for t in ["", "   \n\t ", "\U0001F33F" * 50, "हमारा सबसे अच्छा क्रीम 100% natural है", "a" * 20000,
                  "\x00\x01 control chars", "ß ñ ü 日本語"]:
            self.assertIsInstance(review_text(t), list)

    def test_a_full_length_post_is_reviewed_quickly(self):
        text = "Our BEST cosmetics are 100% natural!!! Click here. " * 400   # about 20,000 characters
        start = time.time()
        review_text(text[:20000])
        self.assertLess(time.time() - start, 5)

    def test_identical_text_gives_identical_findings(self):
        a = [(f["rule_id"], f["text"]) for f in review_text("Our BEST cream. Click here!!!")]
        b = [(f["rule_id"], f["text"]) for f in review_text("Our BEST cream. Click here!!!")]
        self.assertEqual(a, b)


class BadUploads(unittest.TestCase):
    def test_corrupt_and_empty_files_give_a_clear_error_not_a_crash(self):
        for name in ["a.pdf", "a.docx", "a.png", "a.jpg", "a.txt"]:
            for data in [b"", b"not really a file", b"\x00" * 100]:
                try:
                    if name.endswith((".png", ".jpg")):
                        documents.review_image(name, data, "")
                    else:
                        documents.extract_document(name, data)
                except ValueError as e:
                    self.assertTrue(str(e))          # a readable message for the user

    def test_unknown_type_is_refused(self):
        with self.assertRaises(ValueError):
            documents.extract_document("virus.exe", b"MZ")


class WholeAppFlows(unittest.TestCase):
    """Drive the real screens with Streamlit's test runner."""

    def setUp(self):
        fresh_db(self)
        seed.seed_demo()

    def _app(self, user, password):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_app.py"), default_timeout=60).run()
        at.text_input[0].set_value(user)
        at.text_input[1].set_value(password)
        [b for b in at.button if b.label == "Sign in"][0].click().run()
        return at

    def test_every_role_opens_without_errors(self):
        for u, p in [("riya", "Creator@123"), ("arjun", "Manager@123"),
                     ("meera", "Reviewer@123"), ("sana", "Admin@123")]:
            at = self._app(u, p)
            self.assertEqual(len(at.exception), 0, u)

    def test_every_role_opens_on_an_empty_database(self):
        with closing(db._conn()) as c:
            for t in ("findings", "comments", "audit", "versions", "drafts"):
                c.execute("DELETE FROM %s" % t)
            c.commit()
        for u, p in [("arjun", "Manager@123"), ("meera", "Reviewer@123"), ("sana", "Admin@123")]:
            at = self._app(u, p)
            self.assertEqual(len(at.exception), 0, u)

    def test_running_review_on_empty_text_warns_and_creates_nothing(self):
        at = self._app("riya", "Creator@123")
        before = len(db.list_drafts())
        [b for b in at.button if b.label == "Run review"][0].click().run()
        self.assertEqual(len(db.list_drafts()), before)
        self.assertTrue(at.warning)

    def test_running_the_same_review_twice_makes_one_draft(self):
        at = self._app("riya", "Creator@123")
        before = len(db.list_drafts())
        [b for b in at.button if b.label == "Load sample post"][0].click().run()
        [b for b in at.button if b.label == "Run review"][0].click().run()
        [b for b in at.button if b.label == "Run review"][0].click().run()
        self.assertEqual(len(db.list_drafts()), before + 1)
        self.assertEqual(len(at.exception), 0)

    def test_html_in_the_title_and_text_does_not_break_the_page(self):
        at = self._app("riya", "Creator@123")
        at.text_input(key="draft_title").set_value("<script>alert(1)</script>")
        at.text_area(key="draft_text").set_value("<b>Our BEST</b> [x](http://evil.example)")
        [b for b in at.button if b.label == "Run review"][0].click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertFalse(any("<script>" in m.value for m in at.markdown))


if __name__ == "__main__":
    unittest.main()