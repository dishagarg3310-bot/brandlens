import shutil

UI = "app/ui.py"
EX = "app/ui_extras.py"

NEW_BLOCK = '''    with tab_f:
        from app.ui_extras import MODERN_CSS, summary_html, card_html, sort_by_severity

        st.markdown(MODERN_CSS, unsafe_allow_html=True)
        st.markdown(highlight(ver["content"], findings), unsafe_allow_html=True)
        if not findings:
            st.success("No issues found against the approved guidelines.")
        else:
            st.markdown(summary_html(findings), unsafe_allow_html=True)
        can_act = role == "Creator" and draft["status"] in EDITABLE
        DECISION = {"open": "Waiting for your decision", "accepted": "Accepted", "disputed": "Disputed"}
        for f in sort_by_severity([dict(x) for x in findings]):
            st.markdown(card_html(f, DECISION.get(f["status"], f["status"])), unsafe_allow_html=True)
            if can_act:
                a, b, _ = st.columns([1, 1, 4])
                if a.button("Accept", key="acc%d" % f["id"], use_container_width=True):
                    db.set_finding_status(f["id"], "accepted", user, role, did)
                    st.rerun()
                if b.button("Dispute", key="dis%d" % f["id"], use_container_width=True):
                    db.set_finding_status(f["id"], "disputed", user, role, did)
                    st.rerun()
'''

EXTRAS = '''

import html as _html

_SEV = {
    "high": ("#e5484d", "Must fix"),
    "medium": ("#f5a524", "Should fix"),
    "low": ("#d4b106", "Small tweak"),
}
_CAT = {
    "Claim": "Unproven claim",
    "Tone": "Tone of voice",
    "Terminology": "Wrong word for our brand",
    "Accessibility": "Hard to use for some readers",
    "Disclosure": "Missing required info",
}
_DEC = {
    "Accepted": "#30a46c",
    "Disputed": "#e5484d",
    "Waiting for your decision": "#8b8d98",
}

MODERN_CSS = """<style>
.bl-stats{display:flex;flex-wrap:wrap;gap:10px;margin:8px 0 4px}
.bl-stat{flex:1;min-width:120px;padding:12px 14px;border-radius:12px;
 background:var(--secondary-background-color);border:1px solid rgba(128,128,128,.2)}
.bl-stat .n{font-size:26px;font-weight:700;line-height:1.1}
.bl-stat .l{font-size:12px;opacity:.7}
.bl-card{border:1px solid rgba(128,128,128,.25);border-left:5px solid var(--c);
 border-radius:14px;padding:16px 18px;margin:14px 0 6px;
 background:var(--secondary-background-color);box-shadow:0 1px 4px rgba(0,0,0,.08)}
.bl-head{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:12px}
.bl-pill{padding:3px 11px;border-radius:999px;font-size:12px;font-weight:600;
 background:var(--pc);color:#fff}
.bl-chip{padding:3px 11px;border-radius:999px;font-size:12px;
 border:1px solid rgba(128,128,128,.4);opacity:.85}
.bl-diff{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.bl-diff.one{grid-template-columns:1fr}
@media(max-width:640px){.bl-diff{grid-template-columns:1fr}}
.bl-box{border-radius:10px;padding:10px 12px;font-size:14px;word-break:break-word}
.bl-bad{background:rgba(229,72,77,.13)}
.bl-bad .t{text-decoration:line-through;text-decoration-color:rgba(229,72,77,.8)}
.bl-good{background:rgba(48,164,108,.15);font-weight:600}
.bl-lbl{font-size:11px;text-transform:uppercase;letter-spacing:.07em;opacity:.65;
 margin-bottom:4px;font-weight:500}
.bl-why{margin-top:12px;font-size:14px;line-height:1.5}
.bl-meta{margin-top:10px;font-size:12px;opacity:.65;display:flex;
 justify-content:space-between;flex-wrap:wrap;gap:6px}
.bl-dec{font-weight:600;color:var(--dc)}
</style>"""


def _e(x):
    return _html.escape(str(x if x is not None else ""))


def sort_by_severity(findings):
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(findings, key=lambda f: order.get(f.get("severity"), 3))


def summary_html(findings):
    n = len(findings)
    must = sum(1 for f in findings if f["severity"] == "high")
    should = sum(1 for f in findings if f["severity"] == "medium")
    small = sum(1 for f in findings if f["severity"] == "low")
    wait = sum(1 for f in findings if f["status"] == "open")
    items = [
        (n, "Total findings"),
        (must, "🔴 Must fix"),
        (should, "🟠 Should fix"),
        (small, "🟡 Small tweaks"),
        (wait, "Waiting for you"),
    ]
    boxes = "".join(
        '<div class="bl-stat"><div class="n">%d</div><div class="l">%s</div></div>' % (v, l)
        for v, l in items
    )
    return '<div class="bl-stats">%s</div>' % boxes


def card_html(f, decision):
    color, sev = _SEV.get(f.get("severity"), ("#d4b106", "Small tweak"))
    cat = _CAT.get(f.get("category"), f.get("category"))
    ai = '<span class="bl-chip">AI-suggested</span>' if f.get("source") == "ai" else ""
    why = _e(f.get("message"))
    if f.get("fact_id"):
        why += " <i>Approved fact: %s</i>" % _e(f.get("fact_text"))
    bad = ""
    if f.get("text"):
        bad = '<div class="bl-box bl-bad"><div class="bl-lbl">You wrote</div><span class="t">%s</span></div>' % _e(f["text"])
    good = ""
    if f.get("suggestion"):
        good = '<div class="bl-box bl-good"><div class="bl-lbl">Try instead</div>%s</div>' % _e(f["suggestion"])
    cols = "" if (bad and good) else " one"
    diff = '<div class="bl-diff%s">%s%s</div>' % (cols, bad, good) if (bad or good) else ""
    dc = _DEC.get(decision, "#8b8d98")
    return (
        '<div class="bl-card" style="--c:%s">'
        '<div class="bl-head"><span class="bl-pill" style="--pc:%s">%s</span>'
        '<span class="bl-chip">%s</span>%s</div>'
        '%s<div class="bl-why">💡 %s</div>'
        '<div class="bl-meta"><span>Rule: %s (%s)</span>'
        '<span class="bl-dec" style="--dc:%s">%s</span></div></div>'
    ) % (color, color, sev, _e(cat), ai, diff, why,
         _e(f.get("rule_title")), _e(f.get("rule_id")), dc, _e(decision))
'''

with open(UI, encoding="utf-8") as fh:
    lines = fh.read().splitlines()

start = next((i for i, l in enumerate(lines) if l.strip() == "with tab_f:"), None)
end = next((i for i, l in enumerate(lines) if l.strip() == "with tab_c:"), None)
if start is None or end is None or end <= start:
    raise SystemExit("ABORT: tab_f / tab_c markers nahi mile. Kuch change nahi kiya.")

shutil.copy(UI, UI + ".bak2")
lines[start:end] = NEW_BLOCK.rstrip("\n").split("\n") + [""]
with open(UI, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")

with open(EX, encoding="utf-8") as fh:
    ex = fh.read()
if "MODERN_CSS" not in ex:
    shutil.copy(EX, EX + ".bak2")
    with open(EX, "a", encoding="utf-8") as fh:
        fh.write(EXTRAS)

print("DONE: modern UI applied (backup: app/ui.py.bak2)")