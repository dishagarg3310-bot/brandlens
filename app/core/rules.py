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
]

ALLOWED_CAPS = {"PETA", "INDIA"}
MONTHS = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"


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
        pat = r"\b" + re.escape(row["banned"]) + r"\b"
        for m in re.finditer(pat, text, re.I):
            out.append(_finding(
                "Terminology", "medium", row["rule_id"], m.group(0), m.start(), m.end(),
                '"%s" is not an approved term.' % m.group(0),
                'use "%s"' % row["preferred"], passages))

    # Claims (G3)
    for pat, rid, fid, msg, sug in CLAIM_RULES:
        for m in re.finditer(pat, text, re.I):
            out.append(_finding(
                "Claim", "high", rid, m.group(0), m.start(), m.end(), msg, sug,
                passages, fact_map.get(fid) if fid else None))

    # Tone (G1): ALL CAPS and too many exclamation marks
    for m in re.finditer(r"\b[A-Z]{4,}\b", text):
        if m.group(0) in ALLOWED_CAPS:
            continue
        out.append(_finding(
            "Tone", "low", "G1", m.group(0), m.start(), m.end(),
            "ALL CAPS feels like shouting; the brand voice is warm and calm.",
            m.group(0).capitalize(), passages))
    bangs = [i for i, ch in enumerate(text) if ch == "!"]
    if len(bangs) > 1:
        out.append(_finding(
            "Tone", "low", "G1", "!" * len(bangs), bangs[1], bangs[-1] + 1,
            "More than one exclamation mark per post.",
            "keep a single exclamation mark at most", passages))

    # Accessibility (G4)
    for m in re.finditer(r"click here", text, re.I):
        out.append(_finding(
            "Accessibility", "medium", "G4", m.group(0), m.start(), m.end(),
            '"Click here" is not descriptive link text.',
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
            r"\b(till|until|valid|ends?|expires?|through)\b|\b\d{1,2}[/-]\d{1,2}\b|\b"
            + MONTHS + r"\b", text, re.I)
        if not has_date:
            out.append(_finding(
                "Disclosure", "medium", "G6", "", None, None,
                "Discount or offer without an end date.",
                'add the end date, e.g. "valid till 31 Oct"', passages))
    if re.search(r"\b(sponsored|influencer|gifted|partnership|collab)\b", text, re.I):
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
