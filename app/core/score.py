SEVERITY_PENALTY = {"high": 12, "medium": 6, "low": 2}
CATEGORY_CAP = 35


def health_score(findings):
    """Brand health score from 0 to 100, based on rule and AI findings.

    Each finding costs points by severity; one category can cost at most
    CATEGORY_CAP points, so a single noisy category cannot zero the score.
    """
    by_category = {}
    by_severity = {"high": 0, "medium": 0, "low": 0}
    for f in findings:
        sev = f["severity"] if f["severity"] in SEVERITY_PENALTY else "low"
        by_severity[sev] += 1
        cat = f["category"]
        by_category[cat] = by_category.get(cat, 0) + SEVERITY_PENALTY[sev]
    penalty = sum(min(v, CATEGORY_CAP) for v in by_category.values())
    score = max(0, 100 - penalty)
    if score >= 85:
        label, color = "Ready to publish", "#2E7D32"
    elif score >= 60:
        label, color = "Needs work", "#EF6C00"
    else:
        label, color = "At risk", "#C62828"
    counts = {}
    for f in findings:
        counts[f["category"]] = counts.get(f["category"], 0) + 1
    return {
        "score": score,
        "label": label,
        "color": color,
        "by_severity": by_severity,
        "by_category": counts,
    }


def render(findings):
    import pandas as pd
    import streamlit as st

    h = health_score(findings)
    with st.container(border=True):
        left, right = st.columns([1, 1.4], gap="medium")
        with left:
            from app import design
            st.markdown(design.CSS, unsafe_allow_html=True)
            st.markdown(design.ring(h["score"], h["color"], h["label"]), unsafe_allow_html=True)
            st.caption(
                "%d high, %d medium, %d low severity"
                % (h["by_severity"]["high"], h["by_severity"]["medium"], h["by_severity"]["low"])
            )
        with right:
            if h["by_category"]:
                df = pd.DataFrame({"Findings": h["by_category"]})
                st.bar_chart(df, height=170)
            else:
                st.success("No issues found against the approved guidelines.")