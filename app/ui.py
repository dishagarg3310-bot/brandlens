import html

import streamlit as st

from app.core.rules import review_text
from app.db import database as db

ROLES = {
    "Creator": "Riya (Creator)",
    "Manager": "Arjun (Manager)",
    "Reviewer": "Meera (Reviewer)",
    "Admin": "Sana (Admin)",
}
SEV_ICON = {"high": "\U0001F534", "medium": "\U0001F7E0", "low": "\U0001F7E1"}
SEV_BG = {"high": "#ffcdd2", "medium": "#ffe0b2", "low": "#fff9c4"}

SAMPLE = (
    "Our BEST cosmetics are 100% natural and clinically proven!!! "
    "Users love this miracle cream. Get 20% off today. Click here to buy."
)


def set_sample():
    st.session_state["draft_text"] = SAMPLE
    st.session_state["draft_title"] = "Instagram launch post"


def highlight(text, findings):
    spans = sorted(
        [f for f in findings if f["span_start"] is not None], key=lambda f: f["span_start"]
    )
    out, pos = [], 0
    for f in spans:
        s, e = f["span_start"], f["span_end"]
        if s < pos:
            continue
        out.append(html.escape(text[pos:s]))
        out.append(
            '<mark style="background:%s;color:#000;padding:0 3px;border-radius:3px" title="%s">%s</mark>'
            % (SEV_BG[f["severity"]], html.escape(f["category"]), html.escape(text[s:e]))
        )
        pos = e
    out.append(html.escape(text[pos:]))
    return "".join(out).replace("\n", "<br>")


def run_review(user, role):
    text = st.session_state["draft_text"].strip()
    if not text:
        st.warning("Paste some text first.")
        return
    title = st.session_state["draft_title"].strip() or "Untitled draft"
    draft_id = db.create_draft(title, user)
    vid, vno = db.add_version(draft_id, text, user)
    findings = review_text(text)
    db.save_findings(vid, findings)
    db.log(draft_id, user, role, "review_run", "%d findings" % len(findings))
    st.session_state["current_draft"] = draft_id
    st.rerun()


def show_draft(role, user):
    did = st.session_state.get("current_draft")
    if not did:
        st.info("Run a review to see explained findings here.")
        return
    draft = db.get_draft(did)
    ver = db.latest_version(did)
    findings = db.get_findings(ver["id"])
    st.markdown(
        "**%s**  |  version %d  |  status: `%s`" % (draft["title"], ver["version_no"], draft["status"])
    )
    st.markdown(highlight(ver["content"], findings), unsafe_allow_html=True)
    if not findings:
        st.success("No issues found against the approved guidelines.")
        return
    open_n = sum(1 for f in findings if f["status"] == "open")
    st.caption("%d findings, %d still open" % (len(findings), open_n))
    for f in findings:
        with st.container(border=True):
            st.markdown("%s **%s** - %s" % (SEV_ICON[f["severity"]], f["category"], f["message"]))
            if f["text"]:
                st.markdown("Flagged text: `%s`" % f["text"])
            st.markdown("Suggested fix: **%s**" % f["suggestion"])
            with st.expander("Why? Source: %s %s" % (f["rule_id"], f["rule_title"])):
                st.write(f["rule_text"])
                if f["fact_id"]:
                    st.write("Approved fact %s: %s" % (f["fact_id"], f["fact_text"]))
            if role == "Creator":
                a, b, c = st.columns([1, 1, 2])
                if a.button("Accept", key="acc%d" % f["id"]):
                    db.set_finding_status(f["id"], "accepted", user, role, did)
                    st.rerun()
                if b.button("Dispute", key="dis%d" % f["id"]):
                    db.set_finding_status(f["id"], "disputed", user, role, did)
                    st.rerun()
                c.write("Status: **%s**" % f["status"])
            else:
                st.write("Status: **%s**" % f["status"])


def main():
    st.set_page_config(page_title="BrandLens", layout="wide")
    db.init_db()
    st.session_state.setdefault("draft_text", "")
    st.session_state.setdefault("draft_title", "")
    st.session_state.setdefault("current_draft", None)

    with st.sidebar:
        st.title("BrandLens")
        st.caption("Pre-publication brand governance")
        role = st.radio("Demo role (switch any time)", list(ROLES))
        user = ROLES[role]
        st.write("Signed in as **%s**" % user)
        st.divider()
        drafts = db.list_drafts()
        if drafts:
            ids = [d["id"] for d in drafts]
            labels = {d["id"]: "#%d %s (%s)" % (d["id"], d["title"], d["status"]) for d in drafts}
            cur = st.session_state["current_draft"]
            idx = ids.index(cur) if cur in ids else 0
            picked = st.selectbox("Open a draft", ids, index=idx, format_func=lambda i: labels[i])
            st.session_state["current_draft"] = picked
        st.divider()
        st.caption(
            "Demo brand: GreenLeaf Organics (fictional). AI only suggests; humans decide."
        )

    st.header("Review content before it goes live")
    left, right = st.columns([1, 1.3])
    with left:
        st.subheader("1. Draft")
        if role == "Creator":
            st.text_input("Title", key="draft_title")
            st.text_area("Paste your post or copy", key="draft_text", height=220)
            c1, c2 = st.columns(2)
            c1.button("Load sample post", on_click=set_sample, use_container_width=True)
            if c2.button("Run review", type="primary", use_container_width=True):
                run_review(user, role)
        else:
            st.info(
                "Only a Creator submits drafts. Switch the demo role in the sidebar to try it. "
                "You can open any draft from the sidebar."
            )
    with right:
        st.subheader("2. Findings")
        show_draft(role, user)
