import re

import textstat

from .knowledge import load_facts, load_glossary, load_guidelines

# (regex, rule_id, supporting fact id, explanation, suggestion)
CLAIM_RULES = [
    (r"100\s*%\s*natural", "G3", "F1",
     "Absolute claim that the approved sources do not support.",
     "made with 92% naturally derived ingredients"),
    (r"clinically\s+proven", "G3", "F4",
     "Medical-style claim without approved evidence.",
     "dermatologist-tested on 50 volunteers"),
    (r"\bguarantee[ds]?\b", "G3", None,
     "Guarantees cannot be supported by the approved fact sheet.",
     "remove the guarantee or state a verified fact"),
    (r"\bmiracle\b", "G3", None,
     "Hype word that cannot be proven.",
     "remove the word and describe a real ingredient or benefit"),
    (r"\bcures?\b|\bcured\b", "G3", None,
     "Medical or treatment claims are not allowed.",
     "remove treatment language"),
    (r"\bbest\b", "G3", None,
     "Superlative claim without an approved source.",
     "use a supported fact or a softer phrase such as 'one of our favourites'"),
    (r"\b(?:recommended|endorsed|approved)\s+by\s+(?:doctors|dermatologists|experts|medical\s+professionals)(?:\s+across\s+\w+)?",
     "G3", None,
     "Endorsement claim with no approved source behind it.",
     "remove it, or use a verified fact such as 'dermatologist-tested on 50 volunteers'"),
    (r"\b(?:visible\s+)?results\s+in\s+(?:just\s+|only\s+|as\s+little\s+as\s+)?(?:\d+|one|two|three|four|five|six|seven|ten|fourteen)\s+(?:hours?|days?|weeks?)\b",
     "G3", None,
     "A time-bound result promise that the approved facts do not support.",
     "describe the ingredient or routine instead of promising a timeline"),
    (r"\b(?:the\s+)?(?:finest|greatest|most\s+effective)\s+[a-z\- ]{2,25}?\s+in\s+the\s+world\b",
     "G3", None,
     "Superlative claim without an approved source.",
     "use a supported fact, such as 'made with 92% naturally derived ingredients'"),
    (r"\b(?:number\s+one|no\.\s*1|#\s*1)\b",
     "G3", None,
     "Ranking claim without an approved source.",
     "remove the ranking or cite verified market data"),
    (r"\bfree\s+(?:shipping|delivery)\s+on\s+(?:every|all|any)(?:\s+single)?\s+orders?\b",
     "G3", "F3",
     "Free shipping applies only above the approved order value.",
     "free shipping on orders above Rs. 499"),
    (r"\b(?:zero|no)\s+side[\s-]effects?\b",
     "G3", None,
     "Medical-style safety claim that cannot be proven.",
     "remove it and state a tested fact instead"),
    (r"\b(?:safe|suitable|perfect|gentle|works)\s+for\s+(?:every|all|any)\s+skin(?:\s+types?)?\b",
     "G3", "F4",
     "A universal skin-safety claim cannot be proven.",
     "dermatologist-tested on 50 volunteers"),
    (r"\b(?:certified\s+organic|organic\s+certified)\b",
     "G3", None,
     "Organic certification is not listed in the approved facts.",
     "mention only certifications on the fact sheet, e.g. cruelty-free certified by PETA India"),
]

# (regex, explanation, suggestion) for the tone rule G1
TONE_RULES = [
    (r"\b(?:hurry|act\s+now|last\s+chance|don'?t\s+miss\s+out)\b[^.!?\n]*",
     "Pressure language; the brand voice invites rather than pushes.",
     "invite instead, e.g. 'Take a look when you are ready'"),
    (r"\b(?:ultimate|unbeatable|life-changing|revolutionary|game-changing|unbelievable)\b"
     r"(?:\s*,\s*(?:and\s+)?(?:ultimate|unbeatable|life-changing|revolutionary|game-changing|unbelievable))*",
     "Stacked hype words sound exaggerated; the brand voice is warm and calm.",
     "pick one concrete benefit and describe it plainly"),
    (r"\bthanks\s+for\s+nothing(?:,\s*\w+)?|\bugh\b",
     "Sarcastic or negative tone does not fit the warm brand voice.",
     "keep the message friendly and positive"),
]

ALLOWED_CAPS = {"PETA", "INDIA", "SPF", "UVA", "UVB", "FAQ", "USA", "DIY", "FDA", "GST", "AHA", "BHA", "INR"}
MONTHS = (r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|"
          r"aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)")


def _finding(category, severity, rule_id, text, start, end, message, suggestion,
             passages, fact=None):
    p = next((x for x in passages if x["id"] == rule_id), None)
    return {
        "category": category,
        "severity": severity,
        "rule_id": rule_id,
        "rule_title": p["title"] if p else "",
        "rule_text": p["text"] if p else "",
        "fact_id": fact["fact_id"] if fact else None,
        "fact_text": fact["fact"] if fact else None,
        "span": (start, end) if start is not None else None,
        "text": text,
        "message": message,
        "suggestion": suggestion,
        "source": "rule",
        "status": "open",
    }


def review_text(text, passages=None, glossary=None, facts=None):
    passages = passages or load_guidelines()
    glossary = glossary or load_glossary()
    facts = facts or load_facts()
    fact_map = {f["fact_id"]: f for f in facts}
    out = []

    # Terminology (G2)
    for row in glossary:
        # "anti-aging" should also catch "anti aging" and "antiaging"
        pat = r"\b" + r"[-\s]?".join(re.escape(x) for x in row["banned"].split("-")) + r"\b"
        for m in re.finditer(pat, text, re.I):
            out.append(_finding(
                "Terminology", "medium", row["rule_id"], m.group(0), m.start(), m.end(),
                '"%s" is not an approved term.' % m.group(0),
                'use "%s"' % row["preferred"], passages))

    # Claims that must match a number in the approved facts
    f2 = fact_map.get("F2")
    year = re.search(r"(?:19|20)\d{2}", f2["fact"]) if f2 else None
    if year:
        for m in re.finditer(r"\b(?:since|founded\s+in|established\s+in|est\.?)\s+((?:19|20)\d{2})\b", text, re.I):
            if m.group(1) != year.group(0):
                out.append(_finding(
                    "Claim", "high", "G3", m.group(0), m.start(), m.end(),
                    "The year does not match the approved founding year (%s)." % year.group(0),
                    "since %s" % year.group(0), passages, f2))
    f6 = fact_map.get("F6")
    pct = re.search(r"(\d+)\s*%", f6["fact"]) if f6 else None
    if pct:
        for m in re.finditer(r"\b(\d{1,3})\s*%\s*recycled\b", text, re.I):
            if m.group(1) != pct.group(1):
                out.append(_finding(
                    "Claim", "high", "G3", m.group(0), m.start(), m.end(),
                    "The recycled-material share does not match the approved fact (%s%%)." % pct.group(1),
                    "made from %s%% recycled material" % pct.group(1), passages, f6))

    # Claims (G3)
    for pat, rid, fid, msg, sug in CLAIM_RULES:
        for m in re.finditer(pat, text, re.I):
            out.append(_finding(
                "Claim", "high", rid, m.group(0), m.start(), m.end(), msg, sug,
                passages, fact_map.get(fid) if fid else None))

    # Tone (G1): ALL CAPS and too many exclamation marks
    for m in re.finditer(r"\b[A-Z]{3,}\b", text):
        if m.group(0) in ALLOWED_CAPS:
            continue
        out.append(_finding(
            "Tone", "low", "G1", m.group(0), m.start(), m.end(),
            "ALL CAPS feels like shouting; the brand voice is warm and calm.",
            m.group(0).capitalize(), passages))
    bangs = [i for i, ch in enumerate(text) if ch == "!"]
    if len(bangs) > 1:
        run = re.search(r"!{2,}", text)
        if run:
            b_start, b_end = run.start(), run.end()
        else:
            b_start, b_end = bangs[1], bangs[1] + 1
        out.append(_finding(
            "Tone", "low", "G1", text[b_start:b_end], b_start, b_end,
            "More than one exclamation mark per post.",
            "keep a single exclamation mark at most", passages))

    for pat, msg, sug in TONE_RULES:
        for m in re.finditer(pat, text, re.I):
            out.append(_finding(
                "Tone", "low", "G1", m.group(0).strip(), m.start(), m.start() + len(m.group(0).strip()),
                msg, sug, passages))

    # Accessibility (G4)
    for m in re.finditer(r"\b(?:click|tap|press)\s+here\b", text, re.I):
        out.append(_finding(
            "Accessibility", "medium", "G4", m.group(0), m.start(), m.end(),
            '"%s" is not descriptive link text.' % m.group(0),
            'use descriptive text such as "shop the new range"', passages))
    if len(text.split()) >= 20:
        grade = textstat.flesch_kincaid_grade(text)
        if grade > 9:
            out.append(_finding(
                "Accessibility", "low", "G4", "", None, None,
                "Reading level is about grade %.0f; the guideline asks for around grade 8 or easier."
                % grade,
                "use shorter sentences and simpler words", passages))

    # Disclosures (G6)
    if re.search(r"\b\d+\s*%\s*off\b|\bdiscount\b|\bsale\b|\boffer\b", text, re.I):
        has_date = re.search(
            r"\b(till|until|valid|ends?|expires?|through)\b|\b\d{1,2}[/-]\d{1,2}\b|"
            r"\b\d{1,2}(?:st|nd|rd|th)?\s+" + MONTHS + r"\b|\b" + MONTHS + r"\s+\d{1,2}\b",
            text, re.I)
        if not has_date:
            out.append(_finding(
                "Disclosure", "medium", "G6", "", None, None,
                "Discount or offer without an end date.",
                'add the end date, e.g. "valid till 31 Oct"', passages))
    if re.search(r"\b(sponsored|influencer|gifted|partnership|collab|creator\s+partner|brand\s+partner|ambassador|affiliate)\b", text, re.I):
        if not text.strip().lower().startswith("#ad"):
            out.append(_finding(
                "Disclosure", "high", "G6", "", None, None,
                "Sponsored content must start with #ad.",
                "start the caption with #ad", passages))

    out.sort(key=lambda f: (f["span"] is None, f["span"][0] if f["span"] else 0))
    for i, f in enumerate(out, 1):
        f["id"] = "R%d" % i
    return out


if __name__ == "__main__":
    sample = (
        "Our BEST cosmetics are 100% natural and clinically proven!!! "
        "Users love this miracle cream. Get 20% off today. Click here to buy."
    )
    print(sample)
    print("-" * 60)
    for f in review_text(sample):
        print("[%s] %s (%s) '%s' -> %s" % (
            f["severity"], f["category"], f["rule_id"], f["text"], f["suggestion"]))