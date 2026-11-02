"""Apply the fixes a creator has accepted, in one step.

Only findings that
  * the creator accepted,
  * come from the rule engine (never from the AI),
  * have a ready-made replacement (a preferred term, a normal-case word, one exclamation mark,
    or wording taken straight from an approved fact), and
  * still point at exactly the same text in the draft
are changed. Everything else stays untouched and open for a human. The creator sees a preview
first, and the result is saved as a new version, so nothing is lost.
"""
import re

# suggestions that start with one of these are advice for a person, not wording to paste in
ADVICE_WORDS = ("remove", "use", "describe", "mention", "put", "invite", "pick", "keep", "add",
                "start", "say", "write", "increase", "state", "give")


def literal_fix(f):
    """The exact replacement text for a finding, or None when a human has to decide."""
    if f["source"] == "ai" or f["span_start"] is None or f["span_end"] is None:
        return None
    old = (f["text"] or "")
    sug = (f["suggestion"] or "").strip()
    if not old or not sug:
        return None
    cat = f["category"]
    new = None
    if cat == "Terminology":
        m = re.fullmatch(r'use "(.+)"', sug)
        if m:
            new = m.group(1)
            if old[:1].isupper():
                new = new[:1].upper() + new[1:]
    elif cat == "Tone":
        if re.fullmatch(r"!{2,}", old):
            new = "!"
        elif len(old) > 1 and old.isupper() and sug.lower() == old.lower():
            new = sug
    elif cat == "Claim" and f["fact_id"]:
        first = sug.split(" ")[0].lower()
        if first not in ADVICE_WORDS:
            new = sug
    if new is None or new == old:
        return None
    return new


def plan(content, findings):
    """The list of changes that would be made, left to right, without overlaps."""
    items = []
    for f in findings:
        if f["status"] != "accepted":
            continue
        new = literal_fix(f)
        if new is None:
            continue
        s, e = f["span_start"], f["span_end"]
        if not (0 <= s < e <= len(content)) or content[s:e] != f["text"]:
            continue                              # the draft changed since this finding was made
        items.append({"finding_id": f["id"], "start": s, "end": e, "old": f["text"], "new": new,
                      "category": f["category"]})
    items.sort(key=lambda i: (i["start"], -(i["end"] - i["start"])))
    chosen, last_end = [], -1
    for i in items:
        if i["start"] >= last_end:                # skip anything that overlaps an earlier change
            chosen.append(i)
            last_end = i["end"]
    return chosen


def apply(content, changes):
    out, pos = [], 0
    for c in changes:
        out.append(content[pos:c["start"]])
        out.append(c["new"])
        pos = c["end"]
    out.append(content[pos:])
    return "".join(out)


def fixable_count(findings):
    """How many findings (accepted or not) have a ready-made replacement."""
    return sum(1 for f in findings if f["status"] in ("open", "accepted") and literal_fix(f) is not None)