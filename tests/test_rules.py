import unittest

from app.core.rules import review_text


def found(text):
    return review_text(text)


def has(text, category, snippet=None):
    for f in found(text):
        if f["category"] == category and (snippet is None or f["text"].lower() == snippet.lower()):
            return True
    return False


class TerminologyTests(unittest.TestCase):
    def test_banned_term_cosmetics(self):
        self.assertTrue(has("Our cosmetics are lovely.", "Terminology", "cosmetics"))

    def test_banned_term_users(self):
        self.assertTrue(has("Users will love it.", "Terminology", "users"))

    def test_word_boundary_cheaper_is_not_cheap(self):
        self.assertFalse(has("Much cheaper than before.", "Terminology"))

    def test_preferred_term_is_suggested(self):
        f = [x for x in found("Our cosmetics are lovely.") if x["category"] == "Terminology"][0]
        self.assertIn("skincare", f["suggestion"])


class ClaimTests(unittest.TestCase):
    def test_100_percent_natural_links_to_fact_f1(self):
        f = [x for x in found("This cream is 100% natural.") if x["category"] == "Claim"][0]
        self.assertEqual(f["fact_id"], "F1")
        self.assertTrue(f["fact_text"])

    def test_clinically_proven_links_to_fact_f4(self):
        f = [x for x in found("It is clinically proven to work.") if x["category"] == "Claim"][0]
        self.assertEqual(f["fact_id"], "F4")

    def test_guarantee(self):
        self.assertTrue(has("A guaranteed glow.", "Claim", "guaranteed"))

    def test_miracle(self):
        self.assertTrue(has("A miracle in a jar.", "Claim", "miracle"))

    def test_cure(self):
        self.assertTrue(has("This cream can cure dry skin.", "Claim", "cure"))

    def test_best(self):
        self.assertTrue(has("Our best serum yet.", "Claim", "best"))

    def test_claims_are_high_severity(self):
        f = [x for x in found("A miracle in a jar.") if x["category"] == "Claim"][0]
        self.assertEqual(f["severity"], "high")


class ToneTests(unittest.TestCase):
    def test_all_caps(self):
        self.assertTrue(has("Our NEW LAUNCH is here.", "Tone", "LAUNCH"))

    def test_brand_names_in_caps_are_allowed(self):
        self.assertFalse(has("We are certified by PETA India.", "Tone"))

    def test_multiple_exclamation_marks(self):
        self.assertTrue(has("Love it!! Buy now!!", "Tone"))

    def test_single_exclamation_mark_is_fine(self):
        self.assertFalse(has("We are so happy to share this!", "Tone"))


class AccessibilityTests(unittest.TestCase):
    def test_click_here(self):
        self.assertTrue(has("Click here to shop.", "Accessibility", "Click here"))

    def test_descriptive_link_text_is_fine(self):
        self.assertFalse(has("Shop the new skincare range.", "Accessibility"))


class DisclosureTests(unittest.TestCase):
    def test_discount_without_end_date(self):
        self.assertTrue(has("Get 20% off today.", "Disclosure"))

    def test_discount_with_valid_till(self):
        self.assertFalse(has("Get 20% off, valid till 31 Oct.", "Disclosure"))

    def test_discount_with_written_date(self):
        self.assertFalse(has("Sale ends 31 October.", "Disclosure"))

    def test_words_that_start_like_months_do_not_count_as_dates(self):
        self.assertTrue(has("Big sale at the market today.", "Disclosure"))
        self.assertTrue(has("We decide to offer a discount.", "Disclosure"))

    def test_sponsored_post_needs_ad_tag(self):
        self.assertTrue(has("Sponsored by GreenLeaf. Try it.", "Disclosure"))

    def test_sponsored_post_with_ad_tag_is_fine(self):
        self.assertFalse(has("#ad Sponsored by GreenLeaf. Try it.", "Disclosure"))


class ExplainabilityTests(unittest.TestCase):
    SAMPLE = (
        "Our BEST cosmetics are 100% natural and clinically proven!!! "
        "Users love this miracle cream. Get 20% off today. Click here to buy."
    )

    def test_clean_post_has_no_findings(self):
        clean = ("Meet our gentle new moisturiser, made with 92% naturally derived "
                 "ingredients. Free shipping on orders above Rs. 499.")
        self.assertEqual(found(clean), [])

    def test_every_finding_cites_a_guideline(self):
        for f in found(self.SAMPLE):
            self.assertTrue(f["rule_id"].startswith("G"))
            self.assertTrue(f["rule_text"])
            self.assertTrue(f["message"])
            self.assertTrue(f["suggestion"])

    def test_flagged_text_really_exists_in_the_draft(self):
        for f in found(self.SAMPLE):
            if f["span"]:
                s, e = f["span"]
                self.assertEqual(self.SAMPLE[s:e], f["text"])

    def test_findings_are_numbered_in_order(self):
        ids = [f["id"] for f in found(self.SAMPLE)]
        self.assertEqual(ids, ["R%d" % i for i in range(1, len(ids) + 1)])

    def test_sample_post_finds_all_issue_types(self):
        cats = {f["category"] for f in found(self.SAMPLE)}
        self.assertEqual(cats, {"Claim", "Tone", "Terminology", "Accessibility", "Disclosure"})


if __name__ == "__main__":
    unittest.main()