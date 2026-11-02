"""Measure precision and recall of BrandLens findings on the labelled set.

Run from the brandlens folder:
    python -m evaluation.run_eval          # rule engine only
    python -m evaluation.run_eval --ai     # rules + AI layer (needs ANTHROPIC_API_KEY or GEMINI_API_KEY)

Writes evaluation/report.md with the numbers, every miss and every false alarm.
"""
import argparse
import os
import time
from datetime import datetime

from app.core import knowledge, llm, rules
from evaluation.eval_set import POSTS as DEV_POSTS

CATEGORIES = ["Claim", "Terminology", "Tone", "Accessibility", "Disclosure", "Messaging"]


def compatible(pred_text, exp_text):
    if not exp_text and not pred_text:
        return True
    if not exp_text or not pred_text:
        return False
    a, b = pred_text.lower(), exp_text.lower()
    return a in b or b in a


def match(preds, expected):
    """One-to-one matching. Returns (matched pairs, false positives, false negatives)."""
    used = set()
    tp, fn = [], []
    for cat, words in expected:
        hit = None
        for i, p in enumerate(preds):
            if i not in used and p["category"] == cat and compatible(p.get("text") or "", words or ""):
                hit = i
                break
        if hit is None:
            fn.append((cat, words))
        else:
            used.add(hit)
            tp.append((cat, words))
    fp = [(p["category"], p.get("text") or "", p.get("source", "rule")) for i, p in enumerate(preds) if i not in used]
    return tp, fp, fn


def ratio(a, b):
    return a / b if b else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", action="store_true", help="also run the AI layer")
    ap.add_argument("--set", choices=["dev", "holdout"], default="dev",
                    help="dev = the 51 posts the rules were tuned on; holdout = 15 unseen posts")
    args = ap.parse_args()
    if args.set == "holdout":
        from evaluation.holdout_set import POSTS
    else:
        POSTS = DEV_POSTS

    llm.AI_TIMEOUT = int(os.environ.get("AI_TIMEOUT", "30"))   # evaluation can wait longer than the live app
    use_ai = args.ai and llm.ai_available()
    if args.ai and not use_ai:
        print("No ANTHROPIC_API_KEY or GEMINI_API_KEY found: running the rule engine only.")

    passages = knowledge.load_guidelines()
    glossary = knowledge.load_glossary()
    facts = knowledge.load_facts()

    stats = {c: {"tp": 0, "fp": 0, "fn": 0} for c in CATEGORIES}
    misses, alarms = [], []
    for pid, text, expected in POSTS:
        preds = rules.review_text(text, passages, glossary, facts)
        if use_ai:
            if llm.provider() == "gemini":
                time.sleep(7)  # stay under the free-tier requests-per-minute limit
            try:
                preds = preds + llm.review_with_llm(text, passages, facts, preds)
            except Exception as e:  # keep evaluating if one call fails
                print("AI error on %s: %r" % (pid, e))
        tp, fp, fn = match(preds, expected)
        for cat, _ in tp:
            stats[cat]["tp"] += 1
        for cat, _, _ in fp:
            stats.setdefault(cat, {"tp": 0, "fp": 0, "fn": 0})["fp"] += 1
        for cat, _ in fn:
            stats[cat]["fn"] += 1
        misses += [(pid, c, w) for c, w in fn]
        alarms += [(pid, c, t, s) for c, t, s in fp]

    tot = {k: sum(v[k] for v in stats.values()) for k in ("tp", "fp", "fn")}
    mode = ("rules + AI layer (%s)" % llm.provider()) if use_ai else "rule engine only"
    lines = [
        "# BrandLens evaluation report",
        "",
        "Mode: **%s**. Set: %s. Posts: %d. Labelled issues: %d. Run on %s."
        % (mode, args.set, len(POSTS), tot["tp"] + tot["fn"], datetime.now().strftime("%d %b %Y")),
        "",
        "| Category | Correct flags | False alarms | Missed | Precision | Recall |",
        "|---|---|---|---|---|---|",
    ]
    for c, v in stats.items():
        if v["tp"] + v["fp"] + v["fn"] == 0:
            continue
        lines.append("| %s | %d | %d | %d | %.0f%% | %.0f%% |" % (
            c, v["tp"], v["fp"], v["fn"],
            100 * ratio(v["tp"], v["tp"] + v["fp"]), 100 * ratio(v["tp"], v["tp"] + v["fn"])))
    lines.append("| **All** | %d | %d | %d | **%.0f%%** | **%.0f%%** |" % (
        tot["tp"], tot["fp"], tot["fn"],
        100 * ratio(tot["tp"], tot["tp"] + tot["fp"]), 100 * ratio(tot["tp"], tot["tp"] + tot["fn"])))
    lines += ["", "## Missed issues (not flagged)", ""]
    lines += ["- %s [%s] %s" % (p, c, w or "(no single span)") for p, c, w in misses] or ["- none"]
    lines += ["", "## False alarms (flagged but not in the labels)", ""]
    lines += ["- %s [%s] '%s' (%s)" % (p, c, t, s) for p, c, t, s in alarms] or ["- none"]
    report = "\n".join(lines) + "\n"

    out = os.path.join(os.path.dirname(__file__), ("report_ai" if use_ai else "report") + ("_holdout" if args.set == "holdout" else "") + ".md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(report)
    print(report)
    print("Saved", out)


if __name__ == "__main__":
    main()