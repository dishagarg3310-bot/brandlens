"""Held-out evaluation set for BrandLens (fictional brand: GreenLeaf Organics).

These 15 posts were written AFTER the rules were tuned, from the guidelines (G1 to G6)
and the approved facts (F1 to F6) only. The rule engine was not changed to fit them.
Run:  python -m evaluation.run_eval --set holdout            (rules only)
      python -m evaluation.run_eval --set holdout --ai       (rules + AI)

Each post is (id, text, expected_issues); expected_issues is a list of (category, words),
words = the exact text a reviewer should flag, or None when there is no single span.
Review every label yourself and change the ones you disagree with before reporting numbers.
"""

POSTS = [
    # --- clean posts -----------------------------------------------------------
    ("H01", "Our new rose water mist is here. A light spritz can feel refreshing on a warm afternoon. Find it on our website.", []),
    ("H02", "Our soaps come in packaging made from 70% recycled material. Rinse, reuse, repeat.", []),
    ("H12", "We did our best to keep the ingredient list short and simple. Read it on our product page.", []),

    # --- claims (G3): worded differently from the dev set ---------------------------
    ("H03", "Dermatologists across the country swear by our night serum.", [("Claim", "Dermatologists across the country swear by our night serum")]),
    ("H04", "Say goodbye to eczema flare-ups for good with our oat balm.", [("Claim", "Say goodbye to eczema flare-ups for good")]),
    ("H05", "Our serum works on absolutely everyone, and fading every scar is guaranteed.", [("Claim", "works on absolutely everyone"), ("Claim", "guaranteed")]),
    ("H06", "Our dermatologist-tested formula was checked on 500 volunteers.", [("Claim", "500 volunteers")]),

    # --- terminology (G2) ------------------------------------------------------------
    ("H07", "Say no to harsh chemicals this season with our gentle cleanser.", [("Terminology", "chemicals")]),
    ("H08", "Our cheap and cheerful sample sizes are perfect for travel.", [("Terminology", "cheap")]),

    # --- tone (G1) -----------------------------------------------------------------
    ("H09", "OMG you guys!!! The glow-up is REAL!!!", [("Tone", "OMG"), ("Tone", "REAL"), ("Tone", "!!!")]),
    ("H14", "Honestly, if you are not using our sunscreen, you are doing skincare wrong.", [("Tone", "you are doing skincare wrong")]),

    # --- disclosures (G6) -------------------------------------------------------------
    ("H10", "Partnering with GreenLeaf this month, I loved their lip tint! Use code GLOW for a discount.", [("Disclosure", None), ("Disclosure", None)]),
    ("H15", "Sharing my top picks! These were sent to me by GreenLeaf Organics. #sponsored", [("Disclosure", None)]),

    # --- accessibility (G4) -----------------------------------------------------------
    ("H11", "The aforementioned dermatological formulation necessitates application subsequent to cleansing, whereupon epidermal permeability is demonstrably augmented, facilitating enhanced absorption of subsequent compounds.", [("Accessibility", None)]),

    # --- mixed Hindi-English --------------------------------------------------------
    ("H13", "Diwali glow ke liye hamara naya ubtan face pack! 100% natural, sirf aaj ke liye 25% off.", [("Claim", "100% natural")]),
]
