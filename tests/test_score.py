import unittest

from app.core.rules import review_text
from app.core.score import health_score


class HealthScoreTests(unittest.TestCase):
    def test_clean_draft_scores_100(self):
        h = health_score([])
        self.assertEqual(h["score"], 100)
        self.assertEqual(h["label"], "Ready to publish")

    def test_worse_drafts_score_lower(self):
        light = health_score(review_text("Our cosmetics are lovely."))["score"]
        heavy = health_score(review_text("Our BEST cosmetics are 100% natural and clinically proven!!!"))["score"]
        self.assertLess(heavy, light)
        self.assertLess(light, 100)

    def test_score_stays_between_0_and_100(self):
        text = "BEST miracle guaranteed cure clinically proven 100% natural " * 10
        s = health_score(review_text(text))["score"]
        self.assertTrue(0 <= s <= 100)

    def test_one_category_cannot_zero_the_score(self):
        text = "miracle " * 30
        self.assertGreater(health_score(review_text(text))["score"], 50)

    def test_sample_post_is_at_risk(self):
        sample = ("Our BEST cosmetics are 100% natural and clinically proven!!! "
                  "Users love this miracle cream. Get 20% off today. Click here to buy.")
        h = health_score(review_text(sample))
        self.assertEqual(h["label"], "At risk")
        self.assertEqual(h["by_category"]["Claim"], 4)


if __name__ == "__main__":
    unittest.main()