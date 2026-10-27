import streamlit as st

WEIGHTS = {"high": 15, "medium": 8, "low": 3}


def brand_health_score(findings):
    penalty = sum(WEIGHTS.get(f.get("severity", "low"), 3) for f in findings)
    return max(0, 100 - penalty)


def render_summary(findings):
    score = brand_health_score(findings)
    high = sum(1 for f in findings if f.get("severity") == "high")
    medium = sum(1 for f in findings if f.get("severity") == "medium")
    low = sum(1 for f in findings if f.get("severity") == "low")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Brand health", f"{score}/100")
    c2.metric("High", high)
    c3.metric("Medium", medium)
    c4.metric("Low", low)

    if findings:
        cats = {}
        for f in findings:
            cats[f["category"]] = cats.get(f["category"], 0) + 1
        st.caption("Issues by category")
        st.bar_chart(cats)
    else:
        st.success("No issues found. This draft follows the approved guidelines.")


def inject_css():
    st.markdown(
        """
<style>
.block-container { padding-top: 1.5rem; max-width: 1250px; }

[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e3e8df;
    border-left: 5px solid #2e7d32;
    border-radius: 14px;
    padding: 14px 18px;
    box-shadow: 0 2px 8px rgba(30, 60, 30, 0.06);
    transition: transform .15s ease, box-shadow .15s ease;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(30, 60, 30, 0.12);
}

textarea, input[type="text"] {
    border: 1.5px solid #b9cdb5 !important;
    border-radius: 10px !important;
    background: #ffffff !important;
}
textarea:focus, input[type="text"]:focus {
    border-color: #2e7d32 !important;
    box-shadow: 0 0 0 3px rgba(46, 125, 50, 0.15) !important;
}

.stButton > button {
    border-radius: 10px;
    font-weight: 600;
    border: 1.5px solid #2e7d32;
    transition: all .15s ease;
}
.stButton > button:hover {
    background: #2e7d32;
    color: #ffffff;
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(46, 125, 50, 0.25);
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2e7d32, #43a047);
    color: #ffffff;
    border: none;
}

[data-testid="stSidebar"] { border-right: 3px solid #2e7d32; }

[data-testid="stExpander"] {
    border-radius: 12px;
    border: 1px solid #dbe5d6;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
</style>
        """,
        unsafe_allow_html=True,
    )
SEV_LABEL = {
    "high": ("🔴", "Must fix"),
    "medium": ("🟠", "Should fix"),
    "low": ("🟡", "Small tweak"),
}
CAT_LABEL = {
    "Claim": "Unproven claim",
    "Tone": "Tone of voice",
    "Terminology": "Wrong word for our brand",
    "Accessibility": "Hard to use for some readers",
    "Disclosure": "Missing required info",
}


def render_finding(f, status=None):
    icon, sev = SEV_LABEL.get(f.get("severity", "low"), ("🟡", "Small tweak"))
    cat = CAT_LABEL.get(f["category"], f["category"])
    with st.container(border=True):
        st.markdown(f"**{icon} {sev}: {cat}**")
        if f.get("text"):
            st.markdown(f"❌ You wrote: `{f['text']}`")
        if f.get("suggestion"):
            st.markdown(f"✅ Try instead: {f['suggestion']}")
        why = f.get("message", "")
        if f.get("fact_text"):
            why += f" Approved fact: {f['fact_text']}"
        st.markdown(f"💡 Why: {why}")
        st.caption(f"Rule: {f.get('rule_text') or f.get('rule_id', '')}")
        if status:
            st.markdown(f"Your decision: **{str(status).capitalize()}**")


def sort_findings(findings):
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(findings, key=lambda f: order.get(f.get("severity"), 3))

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
