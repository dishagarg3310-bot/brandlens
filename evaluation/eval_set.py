"""Labelled evaluation set for BrandLens (fictional brand: GreenLeaf Organics).

Each post is (id, text, expected_issues). expected_issues is a list of
(category, words) where words is the exact text a reviewer should flag, or None for
issues that have no single span (missing offer end date, missing #ad, reading level).

Labels were written from the brand guidelines (G1 to G6) and the approved facts
(F1 to F6), NOT by running the rule engine, so the rules are tested honestly. Posts
P17 to P24 are deliberately hard: unsupported or contradicted facts, hype and
sarcasm that keyword rules are expected to miss. Review the labels yourself and
change any you disagree with before reporting numbers.
"""

POSTS = [
    # --- clean posts (no issue expected) ---------------------------------------
    ("P01", "Meet our new aloe and oat face wash. It is gentle on skin and made with simple ingredients. Shop the new range on our website.", []),
    ("P02", "Our founder started GreenLeaf Organics in 2019 with one simple idea: honest skincare. Thank you for being part of the journey.", []),
    ("P03", "Free shipping on orders above Rs. 499. Tap the link in our bio to shop the new range.", []),
    ("P04", "Our packaging is made from 70% recycled material. Small steps, kinder choices.", []),
    ("P05", "Cruelty-free is not a trend for us. We are certified cruelty-free by PETA India.", []),
    ("P06", "Winter dryness? Our shea body butter was dermatologist-tested on 50 volunteers. See how it feels on your skin.", []),
    ("P07", "Weekend offer: 20% off all face care, valid till 31 Oct. Shop the new range on our website.", []),
    ("P08", "#ad Thank you to our creator partner for sharing her morning routine with our vitamin C serum.", []),
    ("P09", "Sunday self-care: warm tea, a soft towel and a gentle clay mask. What does your routine look like?", []),
    ("P10", "New in: lavender hand cream with ingredients you can pronounce. Read the full ingredient list on our product page.", []),

    # --- claims (G3) ---------------------------------------------------------------
    ("P11", "Our BEST night cream is here. Wake up to softer skin.", [("Claim", "BEST"), ("Tone", "BEST")]),
    ("P12", "Switch to a 100% natural face wash made for everyday glow.", [("Claim", "100% natural")]),
    ("P13", "Clinically proven to reduce dark circles. Meet our new eye serum.", [("Claim", "Clinically proven")]),
    ("P14", "We guarantee glowing skin in two weeks or your money back.", [("Claim", "guarantee")]),
    ("P15", "This miracle serum fixes everything your skin has been asking for.", [("Claim", "miracle")]),
    ("P16", "Our turmeric balm helps cure acne scars naturally.", [("Claim", "cure")]),
    ("P17", "Recommended by doctors across India. Try our new sunscreen.", [("Claim", "Recommended by doctors across India")]),
    ("P18", "See visible results in just three days with our new serum.", [("Claim", "visible results in just three days")]),
    ("P19", "The finest skincare in the world, made with love.", [("Claim", "The finest skincare in the world")]),
    ("P20", "GreenLeaf Organics has been making skincare since 2015.", [("Claim", "since 2015")]),
    ("P21", "Enjoy free shipping on every single order this month.", [("Claim", "free shipping on every single order")]),
    ("P22", "All our packaging is 100% recycled. Good for you, good for the planet.", [("Claim", "100% recycled")]),
    ("P23", "Zero side effects. Safe for every skin type, always.", [("Claim", "Zero side effects"), ("Claim", "Safe for every skin type")]),
    ("P24", "Organic certified and loved by thousands. Try the new lip balm.", [("Claim", "Organic certified")]),

    # --- terminology (G2) --------------------------------------------------------
    ("P25", "Our users tell us the new body lotion feels light and soft.", [("Terminology", "users")]),
    ("P26", "Discover cosmetics made with plant-based care.", [("Terminology", "cosmetics")]),
    ("P27", "No harsh chemicals in our new shampoo bar.", [("Terminology", "chemicals")]),
    ("P28", "Cheap does not have to mean low quality. Meet our new lip balm.", [("Terminology", "Cheap")]),
    ("P29", "Try our anti-aging night cream before bed.", [("Terminology", "anti-aging")]),
    ("P30", "Our anti aging eye cream is back in stock.", [("Terminology", "anti aging")]),
    ("P31", "Our users and our team love how these cosmetics feel.", [("Terminology", "users"), ("Terminology", "cosmetics")]),
    ("P32", "Affordable skincare that respects your skin. Meet our customers' favourite cleanser.", []),

    # --- tone (G1) ---------------------------------------------------------------
    ("P33", "AMAZING news: our lip balm is back in stock.", [("Tone", "AMAZING")]),
    ("P34", "We are so excited!!! Our new cleanser is here!!!", [("Tone", "!!!")]),
    ("P35", "Hurry, buy now or you will regret it. Stock is almost gone.", [("Tone", "Hurry, buy now or you will regret it")]),
    ("P36", "The ultimate, unbeatable, life-changing moisturiser is finally here.", [("Tone", "ultimate, unbeatable, life-changing")]),
    ("P37", "Oh great, another dry winter. Thanks for nothing, weather. Our body butter is back.", [("Tone", "Thanks for nothing, weather")]),
    ("P38", "Our NATURAL glow range is HERE. Grab it NOW.", [("Tone", "NATURAL"), ("Tone", "HERE"), ("Tone", "NOW")]),
    ("P39", "Sunday reset: a warm shower, a soft towel and our oat body wash.", []),

    # --- accessibility (G4) ------------------------------------------------------
    ("P40", "Read our ingredient guide: click here.", [("Accessibility", "click here")]),
    ("P41", "For the full routine, Click Here to read more on our blog.", [("Accessibility", "Click Here")]),
    ("P42", "Notwithstanding considerable seasonal fluctuations in atmospheric humidity, the formulation incorporates multifunctional emollient constituents engineered to facilitate comprehensive epidermal rehydration throughout prolonged environmental exposure, thereby substantially diminishing perceptible desiccation.", [("Accessibility", None)]),
    ("P43", "Tap here to see our new range.", [("Accessibility", "Tap here")]),
    ("P44", "Not sure which cleanser suits you? Take our two-minute skin quiz on the website.", []),

    # --- disclosures (G6) --------------------------------------------------------
    ("P45", "Get 20% off on all face care today. Stock up on your favourites.", [("Disclosure", None)]),
    ("P46", "Big sale on body care this weekend. Shop the new range.", [("Disclosure", None)]),
    ("P47", "Our creator partner shared her routine with our vitamin C serum. Link in bio.", [("Disclosure", None)]),
    ("P48", "Gifted these goodies by GreenLeaf Organics, and I am in love with the lip balm.", [("Disclosure", None)]),
    ("P49", "#ad Collab with GreenLeaf Organics: my honest review of the clay mask.", []),
    ("P50", "Our festive offer ends on 5 Nov. Get 15% off sitewide.", []),

    # --- the demo post with many issues ----------------------------------------
    ("P51", "Our BEST cosmetics are 100% natural and clinically proven!!! Users love this miracle cream. Get 20% off today. Click here to buy.",
     [("Claim", "BEST"), ("Tone", "BEST"), ("Claim", "100% natural"), ("Claim", "clinically proven"),
      ("Tone", "!!!"), ("Terminology", "Users"), ("Claim", "miracle"), ("Terminology", "cosmetics"),
      ("Disclosure", None), ("Accessibility", "Click here")]),
]
