"""Governance insights: repeated mistakes, unclear guidelines, per-creator trends.

Place this file at app/insights.py.
Data comes from the existing tables (findings, versions, drafts). Only the latest
version of each draft is counted, so a re-reviewed draft is not counted twice.
"""
import pandas as pd
import streamlit as st

from app.db import database as db

MIN_DECIDED = 2          # a rule needs at least this many accept/dispute decisions
DISPUTE_THRESHOLD = 0.4  # dispute rate at or above this => "possibly unclear"

COLUMNS = [
    "finding_id", "category", "severity", "rule_id", "rule_title", "rule_text",
    "status", "source", "draft_id", "creator", "day",
]

_LATEST = (
    "v.id = (SELECT id FROM versions WHERE draft_id = v.draft_id "
    "ORDER BY version_no DESC LIMIT 1)"
)


# ---------------------------------------------------------------- data access
def load_findings(creator=None):
    sql = (
        "SELECT f.id AS finding_id, f.category, f.severity, f.rule_id, f.rule_title, "
        "f.rule_text, f.status, f.source, d.id AS draft_id, d.creator, "
        "substr(v.created_at, 1, 10) AS day "
        "FROM findings f "
        "JOIN versions v ON v.id = f.version_id "
        "JOIN drafts d ON d.id = v.draft_id "
        "WHERE " + _LATEST
    )
    params = ()
    if creator:
        sql += " AND (d.creator = ? OR d.creator LIKE ?)"
        params = (creator, creator.split()[0] + "%")
    rows = db._query(sql, params)
    return pd.DataFrame([dict(r) for r in rows], columns=COLUMNS)


# ------------------------------------------------------- pure analysis helpers
def overview(df):
    n = len(df)
    accepted = int((df["status"] == "accepted").sum()) if n else 0
    disputed = int((df["status"] == "disputed").sum()) if n else 0
    decided = accepted + disputed
    return {
        "findings": n,
        "drafts": int(df["draft_id"].nunique()) if n else 0,
        "high": int((df["severity"] == "high").sum()) if n else 0,
        "ai": int((df["source"] == "ai").sum()) if n else 0,
        "accepted": accepted,
        "disputed": disputed,
        "decided": decided,
        "dispute_rate": (disputed / decided) if decided else 0.0,
    }


def rule_stats(df):
    cols = ["rule_id", "rule", "findings", "accepted", "disputed", "open", "decided", "dispute_rate"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    out = (
        df.groupby(["rule_id", "rule_title"], dropna=False)
        .agg(
            findings=("finding_id", "count"),
            accepted=("status", lambda s: int((s == "accepted").sum())),
            disputed=("status", lambda s: int((s == "disputed").sum())),
            open=("status", lambda s: int((s == "open").sum())),
        )
        .reset_index()
        .rename(columns={"rule_title": "rule"})
    )
    out["decided"] = out["accepted"] + out["disputed"]
    out["dispute_rate"] = (out["disputed"] / out["decided"]).where(out["decided"] > 0, 0.0)
    out = out.sort_values(["findings", "rule_id"], ascending=[False, True]).reset_index(drop=True)
    return out[cols]


def unclear_rules(stats, min_decided=MIN_DECIDED, threshold=DISPUTE_THRESHOLD):
    if stats.empty:
        return stats
    hit = stats[(stats["decided"] >= min_decided) & (stats["dispute_rate"] >= threshold)]
    return hit.sort_values(["dispute_rate", "disputed"], ascending=False).reset_index(drop=True)


def category_counts(df):
    if df.empty:
        return pd.Series(dtype="int64")
    return df["category"].value_counts()


def creator_stats(df):
    cols = ["creator", "drafts", "findings", "per_draft", "high", "disputed", "most_common_category"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    out = (
        df.groupby("creator")
        .agg(
            drafts=("draft_id", "nunique"),
            findings=("finding_id", "count"),
            high=("severity", lambda s: int((s == "high").sum())),
            disputed=("status", lambda s: int((s == "disputed").sum())),
        )
        .reset_index()
    )
    out["per_draft"] = (out["findings"] / out["drafts"]).round(1)
    top = df.groupby("creator")["category"].agg(lambda s: s.value_counts().idxmax())
    out["most_common_category"] = out["creator"].map(top)
    return out.sort_values("findings", ascending=False).reset_index(drop=True)[cols]


def daily_trend(df):
    if df.empty:
        return pd.DataFrame(columns=["findings", "high"])
    return df.groupby("day").agg(
        findings=("finding_id", "count"),
        high=("severity", lambda s: int((s == "high").sum())),
    )


# ------------------------------------------------------------------- the page
def _pct(x):
    return "%d%%" % round(x * 100)


def render_insights(role, user):
    own = role == "Creator"
    df = load_findings(creator=user if own else None)

    st.subheader("Your recurring mistakes" if own else "Governance insights")
    st.caption(
        "Based on the latest version of each draft. "
        + ("Only your own drafts are included." if own else "All drafts are included.")
    )

    if df.empty:
        st.info("No findings yet. Run a review on a draft and this page fills up.")
        return

    o = overview(df)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Findings", o["findings"])
    c2.metric("Drafts reviewed", o["drafts"])
    c3.metric("High-risk", o["high"])
    c4.metric("Dispute rate", _pct(o["dispute_rate"]) if o["decided"] else "n/a")

    stats = rule_stats(df)

    st.markdown("#### Most repeated rules")
    top = stats.head(8)
    st.bar_chart(top.set_index("rule_id")["findings"], height=240)
    show = top[["rule_id", "rule", "findings", "accepted", "disputed", "open"]]
    st.dataframe(show, hide_index=True)

    if own:
        st.markdown("#### How to avoid your top mistakes")
        for _, r in stats.head(3).iterrows():
            text = df.loc[df["rule_id"] == r["rule_id"], "rule_text"].dropna()
            with st.expander("%s %s (%d findings)" % (r["rule_id"], r["rule"], r["findings"])):
                st.write(text.iloc[0] if len(text) else "No rule text stored.")
    else:
        st.markdown("#### Possibly unclear guidelines")
        st.caption(
            "Rules that creators dispute often (at least %s of decisions, with %d or more decisions). "
            "A high dispute rate can mean the guideline is vague or missing an example."
            % (_pct(DISPUTE_THRESHOLD), MIN_DECIDED)
        )
        flagged = unclear_rules(stats)
        if flagged.empty:
            st.success("No rule is disputed often enough to look unclear yet.")
        else:
            view = flagged[["rule_id", "rule", "disputed", "decided", "dispute_rate"]].copy()
            view["dispute_rate"] = view["dispute_rate"].map(_pct)
            st.dataframe(view, hide_index=True)
            st.caption("Suggested action: rewrite the guideline or add an example for the rules above.")

    st.markdown("#### Findings by category")
    st.bar_chart(category_counts(df), height=220)

    if not own:
        st.markdown("#### By creator")
        st.dataframe(creator_stats(df), hide_index=True)

    st.markdown("#### Trend over time")
    trend = daily_trend(df)
    if len(trend) >= 2:
        st.line_chart(trend, height=220)
    else:
        st.caption("Not enough history yet: the trend appears once drafts are reviewed on more than one day.")
