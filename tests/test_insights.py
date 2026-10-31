"""Place this file at tests/test_insights.py."""
import unittest

import pandas as pd

from app.insights import (
    COLUMNS, category_counts, creator_stats, daily_trend, overview, rule_stats, unclear_rules,
)


def _df(rows):
    return pd.DataFrame(rows, columns=COLUMNS)


def _row(fid, cat, sev, rid, title, status, draft, creator, day="2026-10-28", source="rule"):
    return [fid, cat, sev, rid, title, "text of " + rid, status, source, draft, creator, day]


SAMPLE = _df([
    _row(1, "Claim", "high", "G3", "Claims", "accepted", 1, "Riya"),
    _row(2, "Claim", "high", "G3", "Claims", "disputed", 1, "Riya"),
    _row(3, "Claim", "high", "G3", "Claims", "disputed", 2, "Riya", day="2026-10-29"),
    _row(4, "Claim", "medium", "G3", "Claims", "open", 3, "Aman", day="2026-10-29"),
    _row(5, "Terminology", "medium", "G2", "Terminology", "accepted", 3, "Aman"),
    _row(6, "Terminology", "medium", "G2", "Terminology", "accepted", 3, "Aman"),
    _row(7, "Tone", "low", "G1", "Tone of voice", "disputed", 3, "Aman", source="ai"),
])


class TestInsights(unittest.TestCase):
    def test_overview(self):
        o = overview(SAMPLE)
        self.assertEqual(o["findings"], 7)
        self.assertEqual(o["drafts"], 3)
        self.assertEqual(o["high"], 3)
        self.assertEqual(o["ai"], 1)
        self.assertEqual(o["decided"], 6)
        self.assertAlmostEqual(o["dispute_rate"], 3 / 6)

    def test_rule_stats(self):
        s = rule_stats(SAMPLE).set_index("rule_id")
        self.assertEqual(s.loc["G3", "findings"], 4)
        self.assertEqual(s.loc["G3", "disputed"], 2)
        self.assertEqual(s.loc["G3", "open"], 1)
        self.assertAlmostEqual(s.loc["G3", "dispute_rate"], 2 / 3)
        self.assertEqual(s.loc["G2", "dispute_rate"], 0)
        self.assertEqual(list(rule_stats(SAMPLE)["rule_id"])[0], "G3")

    def test_unclear_rules_need_enough_decisions(self):
        flagged = unclear_rules(rule_stats(SAMPLE))
        # G1 has a 100% dispute rate but only one decision, so it is not flagged
        self.assertEqual(list(flagged["rule_id"]), ["G3"])

    def test_creator_stats(self):
        c = creator_stats(SAMPLE).set_index("creator")
        self.assertEqual(c.loc["Riya", "drafts"], 2)
        self.assertEqual(c.loc["Riya", "findings"], 3)
        self.assertEqual(c.loc["Aman", "most_common_category"], "Terminology")

    def test_trend_and_categories(self):
        t = daily_trend(SAMPLE)
        self.assertEqual(list(t.index), ["2026-10-28", "2026-10-29"])
        self.assertEqual(int(category_counts(SAMPLE)["Claim"]), 4)

    def test_empty_data_does_not_crash(self):
        empty = _df([])
        self.assertEqual(overview(empty)["findings"], 0)
        self.assertTrue(rule_stats(empty).empty)
        self.assertTrue(unclear_rules(rule_stats(empty)).empty)
        self.assertTrue(creator_stats(empty).empty)
        self.assertTrue(daily_trend(empty).empty)
        self.assertTrue(category_counts(empty).empty)


if __name__ == "__main__":
    unittest.main()
