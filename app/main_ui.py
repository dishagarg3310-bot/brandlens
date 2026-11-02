import streamlit as st

from app import auth, design, views
from app.core import llm
from app import seed
from app.db import database as db
from app.ui import STATUS_LABEL, journey, render_upload, run_review, set_sample, show_draft


def main():
    st.set_page_config(page_title="BrandLens", page_icon="\U0001F33F", layout="wide")
    db.init_db()
    seed.seed_demo()
    st.markdown(views.EXTRA_CSS, unsafe_allow_html=True)
    st.session_state.setdefault("draft_text", "")
    st.session_state.setdefault("draft_title", "")
    st.session_state.setdefault("current_draft", None)
    if st.session_state.pop("_reset_form", False):      # set by run_review; must run before the widgets exist
        st.session_state["draft_text"] = ""
        st.session_state["draft_title"] = ""

    if not auth.require_login():
        return
    username, role = auth.current()

    with st.sidebar:
        st.markdown("## \U0001F33F BrandLens")
        st.caption("Pre-publication brand governance")
        info = views.ROLE_INFO[role]
        user = info["user"]
        st.write("Signed in as **%s**" % user)
        st.caption(info["tag"])
        if st.button("Switch role (sign out)", use_container_width=True):
            auth.sign_out()
            st.rerun()
        if role == "Creator":
            st.divider()
            drafts = db.list_drafts()
            if drafts:
                ids = [d["id"] for d in drafts]
                labels = {
                    d["id"]: "#%d %s (%s)"
                    % (d["id"], d["title"], STATUS_LABEL.get(d["status"], d["status"]))
                    for d in drafts
                }
                cur = st.session_state["current_draft"]
                idx = ids.index(cur) if cur in ids else 0
                picked = st.selectbox("Open a draft", ids, index=idx, format_func=lambda i: labels[i])
                st.session_state["current_draft"] = picked
        st.divider()
        st.caption("AI review layer: " + ("on" if llm.ai_available() else "off (rule checks only)"))
        if llm.ai_available():
            st.caption("AI only suggests. Emails, phone numbers and links are redacted before text is sent to the AI service.")
        st.caption("Demo brand: GreenLeaf Organics (fictional). AI only suggests; humans decide.")

    views.header(role)
    if role in ("Manager", "Reviewer"):
        views.ensure_selected(role)
    if role != "Admin":
        steps, cur = journey(role)
        design.stepper(steps, cur, info["color"])

    if role == "Creator":
        left, right = st.columns([1, 1.5], gap="large")
        with left:
            with st.container(border=True):
                st.markdown("#### \u270D\uFE0F 1. Write your draft")
                render_upload()
                st.text_input("Title", key="draft_title", max_chars=120)
                st.text_area("Paste your post or copy", key="draft_text", height=240, max_chars=20000)
                if llm.ai_available():
                    st.checkbox("Also ask the AI layer (finds subtler issues, takes a few seconds longer)",
                                value=True, key="use_ai")
                c1, c2 = st.columns(2)
                c1.button("Load sample post", on_click=set_sample, width="stretch")
                if c2.button("Run review", type="primary", width="stretch"):
                    run_review(user, role)
        with right:
            with st.container(border=True):
                st.markdown("#### \U0001F50E 2. Findings and approval")
                show_draft(role, user)
    elif role in ("Manager", "Reviewer"):
        left, right = st.columns([1, 1.6], gap="large")
        with left:
            with st.container(border=True):
                views.queue_panel(role)
        with right:
            with st.container(border=True):
                st.markdown("#### Review and decide")
                did = st.session_state.get("current_draft")
                if not did:
                    st.info("Pick a draft from the queue on the left.")
                else:
                    if role == "Reviewer":
                        views.claim_table(did)
                    show_draft(role, user)
    else:
        views.admin_view()

    if role != "Admin":
        from app.insights import render_insights

        label = "My recurring mistakes" if role == "Creator" else "Insights: repeated mistakes and unclear guidelines"
        with st.expander(label):
            render_insights(role, user)