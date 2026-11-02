"""Apply accepted fixes: only safe, accepted, rule-based, still-matching changes are made."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.core import fixes, llm, score
from app.core.rules import review_text
from app.db import database as db
from app.db import workflow as wf

SAMPLE = ("Our BEST cosmetics are 100% natural and clinically proven!!! Users love this miracle cream. "
          "Get 20% off today. Click here to buy.")


def row(**kw):
    base = dict(id=1, source="rule", category="Terminology", severity="low", rule_id="G2", fact_id=None,
                span_start=0, span_end=5, text="users", suggestion='use "customers"', status="accepted")
    base.update(kw)
    return base


class LiteralFix(unittest.TestCase):
    def test_preferred_term_keeps_the_capital_letter(self):
        self.assertEqual(fixes.literal_fix(row(text="Users")), "Customers")
        self.assertEqual(fixes.literal_fix(row(text="users")), "customers")

    def test_shouting_becomes_normal_case(self):
        f = row(category="Tone", rule_id="G1", text="BEST", suggestion="Best")
        self.assertEqual(fixes.literal_fix(f), "Best")

    def test_many_exclamation_marks_become_one(self):
        f = row(category="Tone", text="!!!", suggestion="keep a single exclamation mark at most")
        self.assertEqual(fixes.literal_fix(f), "!")

    def test_claim_is_replaced_only_with_wording_from_an_approved_fact(self):
        f = row(category="Claim", rule_id="G3", fact_id="F1", text="100% natural",
                suggestion="made with 92% naturally derived ingredients")
        self.assertEqual(fixes.literal_fix(f), "made with 92% naturally derived ingredients")

    def test_advice_is_never_pasted_into_the_draft(self):
        for sug in ["remove the word and describe a real ingredient or benefit",
                    "use a supported fact or a softer phrase", "start the caption with #ad",
                    "add the end date, e.g. \"valid till 31 Oct\""]:
            self.assertIsNone(fixes.literal_fix(row(category="Claim", fact_id="F1", suggestion=sug)), sug)
        self.assertIsNone(fixes.literal_fix(row(category="Claim", fact_id=None, suggestion="since 2019")))

    def test_ai_findings_and_findings_without_a_span_are_never_changed(self):
        self.assertIsNone(fixes.literal_fix(row(source="ai")))
        self.assertIsNone(fixes.literal_fix(row(span_start=None, span_end=None)))


class Plan(unittest.TestCase):
    def test_only_accepted_findings_are_planned(self):
        text = "users"
        self.assertEqual(len(fixes.plan(text, [row(status="accepted", span_end=5)])), 1)
        for st in ("open", "disputed"):
            self.assertEqual(fixes.plan(text, [row(status=st, span_end=5)]), [])

    def test_a_finding_that_no_longer_matches_the_text_is_skipped(self):
        self.assertEqual(fixes.plan("customers", [row(span_end=5)]), [])

    def test_overlapping_changes_keep_the_first_one_only(self):
        a = row(id=1, span_start=0, span_end=5, text="users")
        b = row(id=2, span_start=2, span_end=5, text="ers", suggestion='use "xx"')
        plan = fixes.plan("users", [a, b])
        self.assertEqual([c["finding_id"] for c in plan], [1])

    def test_apply_changes_several_places_correctly(self):
        text = "users and users"
        a = row(id=1, span_start=0, span_end=5)
        b = row(id=2, span_start=10, span_end=15)
        self.assertEqual(fixes.apply(text, fixes.plan(text, [a, b])), "customers and customers")


class EndToEnd(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for p in (mock.patch.object(db, "DB_PATH", Path(tmp.name) / "t.db"),
                  mock.patch.object(llm, "ai_available", lambda: False)):
            p.start()
            self.addCleanup(p.stop)
        db.init_db()

    def test_applying_accepted_fixes_raises_the_score_and_keeps_the_old_version(self):
        did = db.create_draft("t", "Riya")
        vid, _ = db.add_version(did, SAMPLE, "Riya")
        db.save_findings(vid, review_text(SAMPLE))
        for f in db.get_findings(vid):
            db.set_finding_status(f["id"], "accepted", "Riya", "Creator", did)
        rows = db.get_findings(vid)
        plan = fixes.plan(SAMPLE, rows)
        self.assertGreaterEqual(len(plan), 5)
        new = fixes.apply(SAMPLE, plan)
        vid2, vno = db.add_version(did, new, "Riya")
        db.save_findings(vid2, review_text(new))
        self.assertEqual(vno, 2)
        self.assertGreater(score.health_score(review_text(new))["score"], score.health_score(rows)["score"])
        self.assertIn("miracle", new)                       # advice-only findings are left for a human
        self.assertIn("Click here", new)
        self.assertEqual(db.latest_version(did)["content"], new)
        self.assertTrue(wf.set_status(did, "draft", "Riya", "Creator"))


if __name__ == "__main__":
    unittest.main()