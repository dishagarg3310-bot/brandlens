import csv
import io

import streamlit as st

from app.core.knowledge import BRAND_DIR, load_facts, load_glossary, load_guidelines
from app.db import database as db
from app.ui import STATUS_LABEL

ROLE_INFO = {
    "Creator": {
        "user": "Riya (Creator)",
        "color": "#2E7D32",
        "icon": "\u270D\uFE0F",
        "title": "Review content before it goes live",
        "tag": "Write a draft, fix issues, submit for approval",
    },
    "Manager": {
        "user": "Arjun (Manager)",
        "color": "#1565C0",
        "icon": "\U0001F4CB",
        "title": "Approval queue",
        "tag": "Decide on drafts, oldest first",
    },
    "Reviewer": {
        "user": "Meera (Reviewer)",
        "color": "#EF6C00",
        "icon": "\U0001F50D",
        "title": "Compliance review",
        "tag": "Check risky claims, highest risk first",
    },
    "Admin": {
        "user": "Sana (Admin)",
        "color": "#6A1B9A",
        "icon": "\u2699\uFE0F",
        "title": "Brand knowledge and activity",
        "tag": "Manage guidelines, facts and terms",
    },
}

EXTRA_CSS = """
<style>
.role-badge {
    display: inline-block; padding: 4px 14px; border-radius: 999px;
    color: #fff; font-weight: 700; font-size: .85rem; margin-bottom: .2rem;
}
div[data-testid="stMetric"] {
    background: #ffffff; border: 1px solid #dfe8dc; border-radius: 14px;
    padding: 12px 16px; box-shadow: 0 1px 4px rgba(0,0,0,.05);
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #ffffff; border: 1px solid #dfe8dc;
    box-shadow: 0 2px 10px rgba(0,0,0,.04);
}
</style>
"""


def _draft_stats():
    return db._query(
        "SELECT d.id, d.title, d.creator, d.status, d.created_at, "
        "COUNT(f.id) AS total, "
        "COALESCE(SUM(CASE WHEN f.severity = 'high' THEN 1 ELSE 0 END), 0) AS high, "
        "COALESCE(SUM(CASE WHEN f.status = 'disputed' THEN 1 ELSE 0 END), 0) AS disputed "
        "FROM drafts d "
        "LEFT JOIN versions v ON v.draft_id = d.id AND v.version_no = "
        "(SELECT MAX(version_no) FROM versions WHERE draft_id = d.id) "
        "LEFT JOIN findings f ON f.version_id = v.id "
        "GROUP BY d.id ORDER BY d.id DESC"
    )


def header(role):
    info = ROLE_INFO[role]
    stats = _draft_stats()
    st.markdown(
        '<span class="role-badge" style="background:%s">%s %s view</span>'
        % (info["color"], info["icon"], role),
        unsafe_allow_html=True,
    )
    st.title(info["title"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Drafts", len(stats))
    c2.metric("Waiting for review", sum(1 for s in stats if s["status"] == "in_review"))
    c3.metric("Approved", sum(1 for s in stats if s["status"] == "approved"))
    c4.metric(
        "High-risk flags pending",
        sum(s["high"] for s in stats if s["status"] != "approved"),
    )


def _pick(sid, prefix, label, selected):
    if st.button(
        label,
        key="%s%d" % (prefix, sid),
        type="primary" if selected else "secondary",
        width="stretch",
    ):
        st.session_state["current_draft"] = sid
        st.rerun()


def queue_panel(role):
    stats = _draft_stats()
    pending = [s for s in stats if s["status"] == "in_review"]
    if role == "Reviewer":
        pending.sort(key=lambda s: (-s["high"], s["id"]))
        st.markdown("#### Waiting for your decision")
        st.caption("Sorted by risk: most high-risk flags first")
    else:
        pending.sort(key=lambda s: s["id"])
        st.markdown("#### Waiting for your decision")
        st.caption("Oldest first")
    if not pending:
        st.success("The queue is clear. Nothing is waiting for review.")
    current = st.session_state.get("current_draft")
    for s in pending:
        label = "#%d  %s  |  %d findings, %d high-risk, %d disputed" % (
            s["id"], s["title"], s["total"], s["high"], s["disputed"]
        )
        _pick(s["id"], "q", label, current == s["id"])
    others = [s for s in stats if s["status"] != "in_review"]
    with st.expander("All other drafts (%d)" % len(others)):
        for s in others:
            label = "#%d  %s  (%s)" % (s["id"], s["title"], STATUS_LABEL.get(s["status"], s["status"]))
            _pick(s["id"], "o", label, current == s["id"])


def claim_table(did):
    ver = db.latest_version(did)
    if not ver:
        return
    claims = [f for f in db.get_findings(ver["id"]) if f["category"] == "Claim"]
    st.markdown("#### Claim verification")
    if not claims:
        st.caption("No promotional claims found in this version.")
        return
    rows = []
    for f in claims:
        if f["fact_id"]:
            verdict = "Unsupported (approved alternative: %s)" % f["fact_id"]
        else:
            verdict = "Unsupported (no approved fact)"
        rows.append(
            {
                "Claim": f["text"],
                "Verdict": verdict,
                "Approved fact": f["fact_text"] or "-",
                "Creator decision": f["status"],
            }
        )
    st.dataframe(rows, width="stretch", hide_index=True)


def _append_row(path, row):
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerow(row)
    text = path.read_text(encoding="utf-8").rstrip("\r\n")
    path.write_text(text + "\n" + buf.getvalue(), encoding="utf-8")


def admin_view():
    admin_user = ROLE_INFO["Admin"]["user"]
    t1, t2, t3 = st.tabs(["Knowledge base", "Add to knowledge base", "Activity log"])

    with t1:
        with st.container(border=True):
            st.markdown("#### Brand guidelines")
            for p in load_guidelines():
                with st.expander("%s  %s" % (p["id"], p["title"])):
                    st.write(p["text"])
        a, b = st.columns(2, gap="large")
        with a:
            with st.container(border=True):
                st.markdown("#### Approved facts")
                st.dataframe(load_facts(), width="stretch", hide_index=True)
        with b:
            with st.container(border=True):
                st.markdown("#### Terminology")
                st.dataframe(load_glossary(), width="stretch", hide_index=True)

    with t2:
        a, b = st.columns(2, gap="large")
        with a:
            with st.container(border=True):
                st.markdown("#### Add an approved fact")
                with st.form("fact_form", clear_on_submit=True):
                    fact = st.text_input("A statement the brand can prove")
                    ok = st.form_submit_button("Add fact")
                if ok and fact.strip():
                    nxt = max([int(f["fact_id"][1:]) for f in load_facts()] + [0]) + 1
                    _append_row(BRAND_DIR / "facts.csv", ["F%d" % nxt, fact.strip()])
                    db.log(None, admin_user, "Admin", "fact_added", "F%d" % nxt)
                    st.success("Added F%d. New reviews will use it." % nxt)
        with b:
            with st.container(border=True):
                st.markdown("#### Add a banned term")
                with st.form("term_form", clear_on_submit=True):
                    banned = st.text_input("Term to avoid")
                    preferred = st.text_input("Preferred term")
                    ok2 = st.form_submit_button("Add term")
                if ok2 and banned.strip() and preferred.strip():
                    _append_row(BRAND_DIR / "glossary.csv", ["G2", banned.strip(), preferred.strip()])
                    db.log(None, admin_user, "Admin", "term_added", banned.strip())
                    st.success("Added. New reviews will flag '%s'." % banned.strip())

    with t3:
        rows = db._query(
            "SELECT created_at, actor, role, action, detail, draft_id "
            "FROM audit ORDER BY id DESC LIMIT 40"
        )
        with st.container(border=True):
            st.markdown("#### Recent activity")
            if rows:
                st.dataframe([dict(r) for r in rows], width="stretch", hide_index=True)
            else:
                st.caption("No activity yet.")