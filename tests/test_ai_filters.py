"""The AI layer may only add what rules cannot judge: tone, messaging, and claims that
contradict an approved fact. These tests use fake AI answers, so no outside service is called."""
import json
import unittest

from app.core import llm

PASSAGES = [{"id": "G1", "title": "Tone", "text": "Warm and calm."},
            {"id": "G3", "title": "Claims", "text": "Claims need an approved fact."}]
FACTS = [{"fact_id": "F1", "fact": "Products are made with 92% naturally derived ingredients."}]
TEXT = "Try our new sunscreen. We are so excited! Our cream is 100% natural."


def run(items):
    return llm.parse_items(json.dumps(items), TEXT, PASSAGES, FACTS, [], {})


def item(**kw):
    base = {"category": "Tone", "severity": "low", "text": "We are so excited", "message": "m",
            "suggestion": "s", "rule_id": "G1", "fact_id": None, "confidence": "high"}
    base.update(kw)
    return base


class AiFilters(unittest.TestCase):
    def test_tone_and_messaging_findings_are_kept(self):
        self.assertEqual(len(run([item()])), 1)
        self.assertEqual(len(run([item(category="Messaging")])), 1)

    def test_terminology_is_left_to_the_rule_engine(self):
        self.assertEqual(run([item(category="Terminology", text="sunscreen")]), [])

    def test_a_claim_without_an_approved_fact_is_dropped(self):
        self.assertEqual(run([item(category="Claim", rule_id="G3", text="Try our new sunscreen")]), [])

    def test_a_claim_that_cites_an_approved_fact_is_kept(self):
        out = run([item(category="Claim", rule_id="G3", text="100% natural", fact_id="F1")])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["fact_id"], "F1")

    def test_a_claim_citing_a_made_up_fact_is_dropped(self):
        self.assertEqual(run([item(category="Claim", rule_id="G3", text="100% natural", fact_id="F99")]), [])

    def test_at_most_three_ai_findings_are_shown(self):
        words = ["Try", "our", "new", "sunscreen", "excited"]
        many = [item(text=w) for w in words]
        self.assertEqual(len(run(many)), llm.MAX_AI_FINDINGS)

    def test_no_valid_guideline_means_no_finding(self):
        self.assertEqual(run([item(rule_id="G99")]), [])

    def test_unsure_findings_are_marked_for_human_judgement(self):
        out = run([item(confidence="low", severity="high")])
        self.assertEqual(out[0]["severity"], "low")
        self.assertTrue(out[0]["message"].startswith(llm.JUDGEMENT_PREFIX))

    def test_text_that_is_not_in_the_draft_is_dropped(self):
        self.assertEqual(run([item(text="words the creator never wrote")]), [])


if __name__ == "__main__":
    unittest.main()