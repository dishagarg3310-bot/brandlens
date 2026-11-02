import html
import re

import streamlit as st

from app.core.review import review_text
from app.core import score
from app.core import documents
from app.core import fixes
from app.core import llm
from app.db import database as db
from app.db import workflow as wf

ROLES = {
    "Creator": "Riya (Creator)",
    "Manager": "Arjun (Manager)",
    "Reviewer": "Meera (Reviewer)",
    "Admin": "Sana (Admin)",
}
SEV_ICON = {"high": "\U0001F534", "medium": "\U0001F7E0", "low": "\U0001F7E1"}
SEV_BG = {"high": "#ffcdd2", "medium": "#ffe0b2", "low": "#fff9c4"}
STATUS_LABEL = {
    "draft": "Draft",
    "in_review": "In review",
    "changes_requested": "Changes requested",
    "approved": "Approved",
}
EDITABLE = ("draft", "changes_requested")

SAMPLE = (
    "Our BEST cosmetics are 100% natural and clinically proven!!! "
    "Users love this miracle cream. Get 20% off today. Click here to buy."
)


MAX_TEXT = 20000
MAX_TITLE = 120


def md_escape(text):
    """Show user-written text in st.markdown without letting it become links, images or headings."""
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|<>~$])", r"\\\1", str(text or "")).replace("\n", "  \n")


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


UPLOAD_STATE = ("extra_findings", "upload_notes", "image_info")  # last_upload stays so the same file is not re-read


def clear_upload():
    for k in UPLOAD_STATE:
        st.session_state.pop(k, None)


def render_upload():
    """File intake: PDF / DOCX / TXT / image. Call this BEFORE the text box is drawn."""
    types = [t.lstrip(".") for t in documents.TEXT_TYPES + documents.IMAGE_TYPES]
    up = st.file_uploader(
        "Optional: upload a file instead (PDF, DOCX, TXT, PNG, JPG)", type=types,
        help="Files are only read, never executed. Max 5 MB.",
    )
    if up is None:
        return
    is_image = up.name.lower().endswith(documents.IMAGE_TYPES)
    alt = ""
    if is_image:
        st.image(up, width=220)
        alt = st.text_input("Alt text for this image", key="img_alt",
                            placeholder="Describe what the image shows")
    sig = (up.name, up.size, alt)
    if st.session_state.get("last_upload") == sig:
        _show_upload_result()
        return
    try:
        data = up.getvalue()
        if is_image:
            res = documents.review_image(up.name, data, alt)
            st.session_state["extra_findings"] = res["findings"]
            st.session_state["image_info"] = res["info"]
            st.session_state["upload_notes"] = res["notes"]
            parts = [res["text"]] if res["text"] else []
            if alt.strip():
                parts.append("Alt text: " + alt.strip())
            st.session_state["draft_text"] = "\n\n".join(parts) or "[Image: %s]" % up.name
        else:
            res = documents.extract_document(up.name, data)
            st.session_state["extra_findings"] = res["findings"]
            st.session_state["image_info"] = None
            st.session_state["upload_notes"] = res["notes"]
            st.session_state["draft_text"] = res["text"]
        if not st.session_state.get("draft_title"):
            st.session_state["draft_title"] = up.name.rsplit(".", 1)[0]
        st.session_state["last_upload"] = sig
    except ValueError as e:
        st.error(str(e))
        return
    _show_upload_result()


def _show_upload_result():
    for n in st.session_state.get("upload_notes", []):
        st.caption("Note: " + n)
    info = st.session_state.get("image_info")
    if info:
        sw = " ".join(
            '<span style="display:inline-block;width:18px;height:18px;border-radius:4px;'
            'background:%s;border:1px solid #0002"></span>' % c for c in info["swatches"]
        )
        st.markdown(
            "%d\u00d7%d %s \u00b7 main colours: %s \u00b7 brand palette match: **%s**"
            % (info["width"], info["height"], info["format"], sw,
               {True: "yes", False: "no", None: "n/a"}[info["palette_match"]]),
            unsafe_allow_html=True,
        )


def run_review(user, role):
    text = st.session_state["draft_text"].strip()
    if not text:
        st.warning("Paste some text or upload a file first.")
        return
    if len(text) > MAX_TEXT:
        st.warning("This text has %d characters. The limit is %d; please shorten it or split it into parts."
                   % (len(text), MAX_TEXT))
        return
    title = st.session_state["draft_title"].strip()[:MAX_TITLE] or "Untitled draft"
    with st.spinner("Checking the rules, then asking the AI layer (up to %d seconds)..." % llm.AI_TIMEOUT):
        draft_id = db.create_draft(title, user)
        vid, vno = db.add_version(draft_id, text, user)
        findings = review_text(text) + st.session_state.get("extra_findings", [])
        for i, f in enumerate(findings, 1):
            f["id"] = "R%d" % i
        db.save_findings(vid, findings)
        _save_trace(vid)
        db.log(draft_id, user, role, "review_run", "%d findings" % len(findings))
    clear_upload()
    if st.session_state.get("ai_status") in ("failed", "limit"):
        st.session_state["_ai_notice"] = st.session_state["ai_status"]
    st.session_state["_reset_form"] = True   # empty the form so a second click cannot make a duplicate
    st.session_state["current_draft"] = draft_id
    st.rerun()


def post_comment(did, user, role):
    key = "cm_%d" % did
    body = st.session_state.get(key, "").strip()
    if body:
        wf.add_comment(did, user, role, body)
        st.session_state[key] = ""


def apply_fixes_panel(did, user, role, ver, findings):
    """Creator: preview and apply the fixes already accepted, as a new version."""
    ready = fixes.plan(ver["content"], findings)
    total = fixes.fixable_count(findings)
    if not total:
        return
    title = ("Apply %d accepted fix%s in one click" % (len(ready), "" if len(ready) == 1 else "es")
             if ready else "%d finding%s ha%s a ready-made fix" % (total, "" if total == 1 else "s", "s" if total == 1 else "ve"))
    with st.expander("\u2728 " + title, expanded=bool(ready)):
        if not ready:
            st.caption("Press Accept on a finding to include its fix here. You will see exactly what changes "
                       "before anything is saved.")
            return
        st.caption("Only the fixes you accepted are applied. Everything else stays open for you to decide. "
                   "The result is saved as a new version, so nothing is lost.")
        for c in ready:
            st.markdown("%s &nbsp; ~~%s~~ &nbsp;\u2192&nbsp; **%s**" % (c["category"], md_escape(c["old"]), md_escape(c["new"])))
        if st.button("Apply these fixes and save a new version", type="primary", key="applyfix_%d_%d" % (did, ver["version_no"])):
            before = score.health_score(findings)["score"]
            new_text = fixes.apply(ver["content"], ready)
            vid, vno = db.add_version(did, new_text, user)
            fs = review_text(new_text)
            db.save_findings(vid, fs)
            _save_trace(vid)
            wf.set_status(did, "draft", user, role, "new version %d" % vno)
            after = score.health_score(fs)["score"]
            db.log(did, user, role, "fixes_applied", "v%d: %d fixes, health %d to %d" % (vno, len(ready), before, after))
            st.session_state["_fix_result"] = (len(ready), before, after, vno)
            st.rerun()


def workflow_panel(role, user, did, draft, ver, findings):
    status = draft["status"]
    open_n = sum(1 for f in findings if f["status"] == "open")
    disputed = [f for f in findings if f["status"] == "disputed"]

    if status == "approved":
        st.success("This draft is approved by a human reviewer and ready to publish.")
        copy = (
            ver["content"]
            + "\n\n---\nReviewed with BrandLens (AI-assisted findings, human-approved). Draft #%d, version %d."
            % (did, ver["version_no"])
        )
        st.download_button(
            "Download approved copy", copy, file_name="approved_draft_%d.txt" % did, mime="text/plain"
        )
        return

    if role == "Creator" and status in EDITABLE:
        apply_fixes_panel(did, user, role, ver, findings)
        if open_n:
            st.caption("The Submit button appears once every finding is accepted or disputed.")
        elif st.button("Submit for review", type="primary"):
            wf.set_status(did, "in_review", user, role, "version %d" % ver["version_no"])
            st.rerun()   # a second click finds the draft already submitted and changes nothing
        with st.expander("Edit this draft (saves a new version and re-runs the review)"):
            key = "edit_%d_%d" % (did, ver["version_no"])
            st.text_area("Edited text", value=ver["content"], key=key, height=160)
            if st.button("Save as new version and re-review", key="save_" + key):
                new = st.session_state[key].strip()
                if new and new != ver["content"].strip():
                    if len(new) > MAX_TEXT:
                        st.warning("The limit is %d characters." % MAX_TEXT)
                    else:
                        vid, vno = db.add_version(did, new, user)
                        fs = review_text(new)
                        db.save_findings(vid, fs)
                        _save_trace(vid)
                        wf.set_status(did, "draft", user, role, "new version %d" % vno)
                        db.log(did, user, role, "new_version", "v%d, %d findings" % (vno, len(fs)))
                        st.rerun()
                else:
                    st.warning("Change the text first.")
    elif role in ("Manager", "Reviewer") and status == "in_review":
        if disputed:
            st.warning(
                "The creator disputed %d finding(s). Check them before approving." % len(disputed)
            )
        note = st.text_area("Note to the creator", key="note_%d" % did, height=90)
        a, b = st.columns(2)
        if a.button("Approve", type="primary", width='stretch'):
            if wf.set_status(did, "approved", user, role, "approved") and note.strip():
                wf.add_comment(did, user, role, note.strip())
            st.rerun()
        if b.button("Request changes", width='stretch'):
            if not note.strip():
                st.warning("Add a note explaining what to change.")
            else:
                if wf.set_status(did, "changes_requested", user, role, "changes requested"):
                    wf.add_comment(did, user, role, note.strip())
                st.rerun()
    elif status == "in_review":
        st.info("Waiting for a Manager or Reviewer to decide.")
    elif role in ("Manager", "Reviewer"):
        if status == "changes_requested":
            st.info("Changes were requested and the Creator is revising this draft, so there is nothing to "
                    "decide yet. To approve or request changes, open a draft from "
                    "**Waiting for your decision** on the left.")
        else:
            st.info("The Creator has not submitted this draft yet, so there is nothing to decide. "
                    "To approve or request changes, open a draft from **Waiting for your decision** on the left.")
    else:
        st.info("Waiting for the Creator to resolve findings and submit.")


def journey(role):
    """(step names, index of the current step) for the progress bar under the banner."""
    did = st.session_state.get("current_draft")
    draft = db.get_draft(did) if did else None
    status = draft["status"] if draft else None
    open_n = 0
    if draft:
        ver = db.latest_version(did)
        open_n = sum(1 for f in db.get_findings(ver["id"]) if f["status"] == "open")
    if role == "Creator":
        steps = ["Write and review", "Fix the findings", "Submit", "Approved"]
        if status is None:
            cur = 0
        elif status in EDITABLE:
            cur = 1 if open_n else 2
        elif status == "in_review":
            cur = 3
        else:
            cur = 4
    else:
        steps = ["Pick a draft", "Check the findings", "Decide"]
        cur = 1 if status == "in_review" else (3 if status == "approved" else 0)
    return steps, cur


REDACTION_NAMES = {"EMAIL": "email address", "URL": "web link", "UPI": "UPI id",
                   "ID": "ID number (PAN or Aadhaar style)", "PHONE": "phone number"}


def _save_trace(version_id):
    trace = st.session_state.pop("ai_trace", None)
    if trace:
        db.save_ai_trace(version_id, trace)


def ai_trace_panel(ver):
    """Show exactly what the AI layer was given for this version, and what came back."""
    t = db.get_ai_trace(ver["id"])
    with st.expander("\U0001F50E What the AI saw: privacy and transparency"):
        if t is None:
            st.caption("There is no AI record for this version. It was made before AI records were kept.")
            return
        status = t.get("status")
        if status == "off":
            why = ("The AI layer was switched off for this review."
                   if t.get("reason") == "switched_off" else "No AI service is set up on this server.")
            st.success("No outside service was called for this review. " + why +
                       " Every finding came from the rule engine and the approved guidelines and facts.")
            return
        if status == "limit":
            st.info("The AI limit for this session was reached, so this review used rule checks only. "
                    "Nothing was sent to an outside service.")
            return
        service = t.get("service") or "the configured AI service"
        if status == "failed":
            st.warning("%s did not answer in time (%s s). The review continued with rule checks only."
                       % (service, t.get("seconds", "?")))
        elif t.get("cached"):
            st.markdown("**Service:** %s. This text had already been checked in this session, so the earlier "
                        "answer was reused and nothing new was sent." % md_escape(service))
        else:
            st.markdown("**Service:** %s &nbsp;|&nbsp; **Answered in:** %s seconds" % (md_escape(service), t.get("seconds", "?")))
        kinds = t.get("redactions") or {}
        if kinds:
            parts = ["%d %s%s" % (n, REDACTION_NAMES.get(k, k.lower()), "" if n == 1 else "s") for k, n in kinds.items()]
            st.markdown("**Personal data protected:** %s replaced with placeholders such as [EMAIL_1] before "
                        "sending. The AI never saw the originals." % ", ".join(parts))
        else:
            st.markdown("**Personal data protected:** no emails, phone numbers, links or ID numbers were found in this draft.")
        if t.get("sent_text") is not None:
            st.markdown("**The text that was sent (after protection):**")
            st.code(t["sent_text"], language=None, wrap_lines=True)
        passages = t.get("passages") or []
        if passages:
            st.markdown("**Guideline passages the AI was allowed to use:** " +
                        ", ".join("%s (%s)" % (p["id"], md_escape(p["title"])) for p in passages))
        if t.get("facts"):
            st.markdown("**Approved facts shown to it:** " + ", ".join(t["facts"]))
        if status == "ok" and "returned" in t:
            st.markdown("**What came back:** %d suggestion%s. %d passed our checks (a real guideline, wording that is "
                        "really in the draft, an allowed type) and show up as AI-suggested findings; the rest were discarded."
                        % (t["returned"], "" if t["returned"] == 1 else "s", t.get("shown", 0)))
        st.caption("AI findings are suggestions only. A person accepts, disputes or approves every one.")


def next_step_box(role, draft, open_n, disputed_n):
    from app import design
    status = draft["status"]
    if status == "approved":
        design.next_step("This draft is approved and ready to publish.", "You can download the final copy below.", "ok")
    elif role == "Creator" and status in EDITABLE:
        prefix = "A reviewer asked for changes. Read their comment, edit the draft, then continue. " \
            if status == "changes_requested" else ""
        if open_n:
            design.next_step(
                "%sNext: look at the %d findings below and press Accept or Dispute on each one." % (prefix, open_n),
                "Accept = you agree and will fix it. Dispute = you disagree, a human reviewer will decide.")
        else:
            design.next_step("%sAll findings are handled. Next: press Submit for review." % prefix,
                             "A Manager or Reviewer will approve it or ask for changes.")
    elif status == "in_review" and role in ("Manager", "Reviewer"):
        design.next_step("Next: read the findings and the draft, then press Approve or Request changes.",
                         "%d finding(s) disputed by the creator." % disputed_n if disputed_n else "", "")
    elif status == "in_review":
        design.next_step("Submitted. Waiting for a Manager or Reviewer to decide.", "", "wait")
    elif role in ("Manager", "Reviewer"):
        design.next_step("Nothing to decide on this draft yet.",
                         "Pick a draft from 'Waiting for your decision' on the left.", "wait")
    else:
        design.next_step("Waiting for the Creator to resolve the findings and submit.", "", "wait")


def show_draft(role, user):
    did = st.session_state.get("current_draft")
    if not did:
        st.info("Run a review to see explained findings here.")
        return
    draft = db.get_draft(did)
    ver = db.latest_version(did)
    findings = db.get_findings(ver["id"])
    st.markdown(
        "**%s**  |  version %d  |  status: **%s**"
        % (md_escape(draft["title"]), ver["version_no"], STATUS_LABEL.get(draft["status"], draft["status"]))
    )
    result = st.session_state.pop("_fix_result", None)
    if result:
        from app import design
        n, before, after, vno = result
        design.next_step("Applied %d fix%s: brand health went from %d to %d." % (n, "" if n == 1 else "es", before, after),
                         "Saved as version %d. The older version is still in the history tab." % vno, "ok")
    notice = st.session_state.pop("_ai_notice", None)
    if notice == "failed":
        st.warning("The AI layer did not answer in time, so this review used the rule checks only. "
                   "Open 'Edit this draft' and save again to retry.")
    elif notice == "limit":
        st.warning("The AI review limit for this session was reached, so this review used the rule checks only.")
    open_n = sum(1 for f in findings if f["status"] == "open")
    disputed_n = sum(1 for f in findings if f["status"] == "disputed")
    next_step_box(role, draft, open_n, disputed_n)
    st.caption("Brand health: how closely this draft follows the brand guidelines (100 means no issues found).")
    score.render(findings)
    workflow_panel(role, user, did, draft, ver, findings)
    from app import export
    with st.expander("Export: download the review as a report or CSV"):
        d1, d2 = st.columns(2)
        d1.download_button(
            "Download report (.md)", export.markdown_report(draft, ver, findings, score.health_score(findings)),
            file_name="brandlens_review_%d_v%d.md" % (did, ver["version_no"]), mime="text/markdown",
            use_container_width=True)
        d2.download_button(
            "Download findings (.csv)", export.findings_csv(findings),
            file_name="brandlens_findings_%d_v%d.csv" % (did, ver["version_no"]), mime="text/csv",
            use_container_width=True)
    ai_trace_panel(ver)

    from app.theme import apply_theme
    apply_theme()

    tab_f, tab_c, tab_h = st.tabs(["Findings", "Comments", "Versions and audit"])

    with tab_f:
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

    with tab_c:
        comments = wf.list_comments(did)
        if not comments:
            st.caption("No comments yet.")
        for c in comments:
            st.markdown("**%s** (%s)  \n%s" % (md_escape(c["author"]), c["role"], md_escape(c["body"])))
            st.caption(c["created_at"])
        st.text_input("Add a comment", key="cm_%d" % did)
        st.button("Post comment", on_click=post_comment, args=(did, user, role))

    with tab_h:
        st.markdown("**Revision history**")
        for v in wf.list_versions(did):
            with st.expander("Version %d by %s at %s" % (v["version_no"], v["created_by"], v["created_at"])):
                st.text(v["content"])
        st.markdown("**Audit trail**")
        rows = [
            {"time": a["created_at"], "who": a["actor"], "role": a["role"],
             "action": a["action"], "detail": a["detail"]}
            for a in wf.list_audit(did)
        ]
        st.dataframe(rows, width='stretch', hide_index=True)


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
            labels = {
                d["id"]: "#%d %s (%s)" % (d["id"], d["title"], STATUS_LABEL.get(d["status"], d["status"]))
                for d in drafts
            }
            cur = st.session_state["current_draft"]
            idx = ids.index(cur) if cur in ids else 0
            picked = st.selectbox("Open a draft", ids, index=idx, format_func=lambda i: labels[i])
            st.session_state["current_draft"] = picked
        st.divider()
        st.caption("Demo brand: GreenLeaf Organics (fictional). AI only suggests; humans decide.")

    st.header("Review content before it goes live")
    left, right = st.columns([1, 1.3])
    with left:
        st.subheader("1. Draft")
        if role == "Creator":
            st.text_input("Title", key="draft_title")
            st.text_area("Paste your post or copy", key="draft_text", height=220)
            c1, c2 = st.columns(2)
            c1.button("Load sample post", on_click=set_sample, width='stretch')
            if c2.button("Run review", type="primary", width='stretch'):
                run_review(user, role)
        else:
            st.info(
                "Only a Creator submits drafts. Switch the demo role in the sidebar to try it. "
                "You can open any draft from the sidebar."
            )
    with right:
        st.subheader("2. Findings and approval")
        show_draft(role, user)