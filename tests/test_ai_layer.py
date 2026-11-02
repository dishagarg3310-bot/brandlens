import unittest

from app.core.llm import JUDGEMENT_PREFIX, parse_items
from app.core.redaction import has_pii, redact, restore
from app.core.retrieval import retrieve

PASSAGES = [
    {"id": "G1", "title": "Tone of voice", "text": "Warm and calm. Avoid hype."},
    {"id": "G3", "title": "Claims", "text": "Only state facts from the approved fact sheet."},
]
FACTS = [{"fact_id": "F2", "fact": "GreenLeaf Organics was founded in 2019."}]


class TestRedaction(unittest.TestCase):
    def test_email_phone_url_are_replaced(self):
        text = "Mail hello@greenleaf.in or call 98765 43210, see https://greenleaf.in/shop today."
        safe, mapping = redact(text)
        self.assertNotIn("hello@greenleaf.in", safe)
        self.assertNotIn("98765", safe)
        self.assertNotIn("https://", safe)
        self.assertIn("[EMAIL_1]", safe)
        self.assertIn("[PHONE_1]", safe)
        self.assertIn("[URL_1]", safe)
        self.assertEqual(restore(safe, mapping), text)

    def test_same_value_gets_same_token(self):
        safe, mapping = redact("a@b.in and again a@b.in")
        self.assertEqual(safe.count("[EMAIL_1]"), 2)
        self.assertEqual(len(mapping), 1)

    def test_pan_and_aadhaar(self):
        safe, _ = redact("PAN ABCDE1234F and 1234 5678 9012")
        self.assertNotIn("ABCDE1234F", safe)
        self.assertNotIn("1234 5678 9012", safe)

    def test_normal_marketing_text_is_unchanged(self):
        text = "Free shipping on orders above Rs. 499. Founded in 2019 with 92% ingredients."
        safe, mapping = redact(text)
        self.assertEqual(safe, text)
        self.assertEqual(mapping, {})
        self.assertFalse(has_pii(text))


class TestRetrieval(unittest.TestCase):
    ITEMS = [
        {"id": "A", "text": "Shipping and delivery: orders ship within two days."},
        {"id": "B", "text": "Tone of voice should be warm and calm."},
        {"id": "C", "text": "Claims must match the approved fact sheet."},
        {"id": "D", "text": "Use customers not users in all copy."},
        {"id": "E", "text": "Images need descriptive alt text."},
        {"id": "F", "text": "Discount posts must state an end date."},
    ]

    def test_small_corpus_returns_everything(self):
        self.assertEqual(len(retrieve("anything", self.ITEMS[:3], lambda i: i["text"], k=4)), 3)

    def test_picks_relevant_item(self):
        got = retrieve("when will my shipping arrive", self.ITEMS, lambda i: i["text"], k=1, min_items=1)
        self.assertEqual([i["id"] for i in got], ["A"])

    def test_no_match_still_returns_minimum_context(self):
        got = retrieve("zzz qqq", self.ITEMS, lambda i: i["text"], k=2, min_items=3)
        self.assertEqual(len(got), 3)

    def test_keeps_original_order(self):
        got = retrieve("tone warm calm and alt text images", self.ITEMS, lambda i: i["text"], k=2, min_items=1)
        ids = [i["id"] for i in got]
        self.assertEqual(ids, sorted(ids))


class TestParseItems(unittest.TestCase):
    TEXT = "Our brand has been here since 2015. Mail hello@greenleaf.in for the BEST deal."

    def _raw(self, **over):
        item = {
            "category": "Claim", "severity": "high", "text": "since 2015",
            "message": "Contradicts the approved founding year.",
            "suggestion": "since 2019", "rule_id": "G3", "fact_id": "F2", "confidence": "high",
        }
        item.update(over)
        import json
        return "Here you go: " + json.dumps([item])

    def test_valid_item_becomes_finding(self):
        out = parse_items(self._raw(), self.TEXT, PASSAGES, FACTS, [])
        self.assertEqual(len(out), 1)
        f = out[0]
        self.assertEqual(f["source"], "ai")
        self.assertEqual(f["severity"], "high")
        self.assertEqual(f["rule_id"], "G3")
        self.assertEqual(f["fact_id"], "F2")
        self.assertEqual(f["text"], "since 2015")

    def test_unknown_rule_id_is_dropped(self):
        self.assertEqual(parse_items(self._raw(rule_id="G9"), self.TEXT, PASSAGES, FACTS, []), [])

    def test_rule_not_retrieved_is_dropped(self):
        out = parse_items(self._raw(), self.TEXT, PASSAGES, FACTS, [], allowed_rule_ids=["G1"])
        self.assertEqual(out, [])

    def test_quote_not_in_draft_is_dropped(self):
        self.assertEqual(parse_items(self._raw(text="not in the draft"), self.TEXT, PASSAGES, FACTS, []), [])

    def test_overlap_with_existing_finding_is_dropped(self):
        existing = [{"span": (30, 40)}]
        self.assertEqual(parse_items(self._raw(), self.TEXT, PASSAGES, FACTS, existing), [])

    def test_low_or_missing_confidence_needs_human_judgement(self):
        for conf in ("low", None):
            out = parse_items(self._raw(confidence=conf), self.TEXT, PASSAGES, FACTS, [])
            self.assertEqual(out[0]["severity"], "low")
            self.assertTrue(out[0]["message"].startswith(JUDGEMENT_PREFIX))

    def test_bad_json_returns_nothing(self):
        self.assertEqual(parse_items("[not json", self.TEXT, PASSAGES, FACTS, []), [])
        self.assertEqual(parse_items("no list here", self.TEXT, PASSAGES, FACTS, []), [])

    def test_placeholders_are_restored_to_find_the_span(self):
        mapping = {"[EMAIL_1]": "hello@greenleaf.in"}
        out = parse_items(
            self._raw(text="Mail [EMAIL_1] for the BEST deal", rule_id="G1", category="Tone"),
            self.TEXT, PASSAGES, FACTS, [], mapping,
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["text"], "Mail hello@greenleaf.in for the BEST deal")


if __name__ == "__main__":
    unittest.main()
