"""Download helpers: a readable review report and a CSV of the findings."""
import csv
import io
from datetime import datetime

SEV = {"high": "Must fix", "medium": "Should fix", "low": "Small tweak"}


def findings_csv(findings):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "category", "severity", "flagged_text", "why", "suggestion",
                "rule", "approved_fact", "source", "decision"])
    for n, f in enumerate(findings, 1):
        w.writerow([n, f["category"], SEV.get(f["severity"], f["severity"]), f["text"] or "",
                    f["message"], f["suggestion"] or "", f["rule_id"] or "", f["fact_id"] or "",
                    f["source"], f["status"]])
    return buf.getvalue().encode("utf-8-sig")  # BOM so Excel opens it correctly


def markdown_report(draft, version, findings, health):
    lines = [
        "# BrandLens review report", "",
        "- Draft: **%s** (version %d)" % (draft["title"], version["version_no"]),
        "- Status: %s" % draft["status"],
        "- Brand health: **%d/100** (%s)" % (health["score"], health["label"]),
        "- Generated: %s" % datetime.now().strftime("%d %b %Y, %H:%M"),
        "- AI findings are suggestions only. A human accepts, disputes or approves every item.", "",
        "## Draft text", "", "> " + version["content"].replace("\n", "\n> "), "",
        "## Findings (%d)" % len(findings), "",
    ]
    if not findings:
        lines.append("No issues found against the approved guidelines.")
    for n, f in enumerate(findings, 1):
        lines += [
            "### %d. %s: %s" % (n, f["category"], SEV.get(f["severity"], f["severity"])),
            "- Flagged: %s" % (f["text"] or "(whole post)"),
            "- Why: %s" % f["message"],
            "- Suggested fix: %s" % (f["suggestion"] or "n/a"),
            "- Based on: rule %s%s" % (f["rule_id"] or "n/a", (", approved fact " + f["fact_id"]) if f["fact_id"] else ""),
            "- Found by: %s | Decision: %s" % ("AI" if f["source"] == "ai" else "rule engine", f["status"]), "",
        ]
    return "\n".join(lines).encode("utf-8")