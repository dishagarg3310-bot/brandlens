import csv
import html
import io

import streamlit as st

from app.core import assets, documents, guideline_import, knowledge
from app.core.knowledge import BRAND_DIR, load_facts, load_glossary, load_guidelines
from app.db import database as db
from app.ui import STATUS_LABEL, md_escape

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
    from app import design
    from app.core import llm

    ai_label = "AI layer on" if llm.ai_available() else "Rule checks (AI off)"
    st.markdown(design.CSS, unsafe_allow_html=True)
    design.hero(role, info, ai_label)
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


def ensure_selected(role):
    """Open the first draft that needs a decision, so the progress bar and the screen agree."""
    stats = _draft_stats()
    pending = [s for s in stats if s["status"] == "in_review"]
    pending.sort(key=(lambda s: (-s["high"], s["id"])) if role == "Reviewer" else (lambda s: s["id"]))
    if pending and st.session_state.get("current_draft") not in [s["id"] for s in stats]:
        st.session_state["current_draft"] = pending[0]["id"]


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
    if pending and st.session_state.get("current_draft") not in [s["id"] for s in stats]:
        st.session_state["current_draft"] = pending[0]["id"]   # open the first draft that needs a decision
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


def _forget_ai_answers():
    """Guidelines or colours changed, so earlier AI answers (kept per session) are out of date."""
    st.session_state.pop("ai_cache", None)


def _swatches(colours):
    chips = []
    for c in colours:
        if not assets.HEX.match(str(c.get("hex", ""))):
            continue
        chips.append(
            '<span style="display:inline-flex;align-items:center;gap:8px;margin:0 14px 8px 0">'
            '<span style="width:26px;height:26px;border-radius:8px;background:%s;border:1px solid rgba(0,0,0,.25)"></span>'
            "<span><b>%s</b> <span style='opacity:.7'>%s</span></span></span>"
            % (c["hex"], html.escape(str(c.get("name", ""))), c["hex"].upper()))
    return "".join(chips) or "<i>No colours yet.</i>"


def brand_assets_panel():
    """What a Creator can reuse: the approved colours and images."""
    store = assets.load_assets()
    st.caption("Use these approved colours and images in your content. They are kept by the Admin.")
    st.markdown(_swatches(store["colours"]), unsafe_allow_html=True)
    if not store["images"]:
        st.caption("No approved images have been added yet.")
    for img in store["images"]:
        c1, c2 = st.columns([1, 3])
        try:
            c1.image(assets.image_bytes(img), width=110)
        except OSError:
            c1.caption("(file missing)")
        c2.markdown("**%s**  \nAlt text: %s%s" % (md_escape(img["name"]), md_escape(img["alt"]),
                                                  ("  \nUse: " + md_escape(img["usage"])) if img["usage"] else ""))
        try:
            c2.download_button("Download", assets.image_bytes(img), file_name=img["file"], key="dl_" + img["id"])
        except OSError:
            pass


def _guideline_import_tab(admin_user):
    import pandas as pd

    with st.container(border=True):
        st.markdown("#### Import guidelines from a document")
        st.caption("Upload your brand book (PDF, Word, Markdown or text). BrandLens splits it into passages, "
                   "you check them, and only the ones you tick are added. Imported passages get new ids (G7, G8, ...). "
                   "They are used by the AI layer and shown to reviewers; the exact-match rules for G1 to G6 stay as they are.")
        st.caption("Privacy: guideline passages can be sent to the AI service so it can judge drafts against them. "
                   "Passages with emails, phone numbers, links or ID numbers are left out unless you remove those details.")
        up = st.file_uploader("Brand book or guideline document", type=["pdf", "docx", "md", "txt"], key="gl_upload")
        if up is None:
            return
        sig = (up.name, up.size)
        if st.session_state.get("gl_sig") != sig:
            st.session_state.pop("gl_rows", None)
            try:
                res = documents.extract_document(up.name, up.getvalue())
                found = guideline_import.split_passages(res["text"])
                if not found:
                    st.warning("No readable text was found in this file.")
                    return
                st.session_state["gl_rows"] = guideline_import.prepare(found, load_guidelines())
                st.session_state["gl_notes"] = res["notes"]
                st.session_state["gl_sig"] = sig
            except ValueError as e:
                st.error(str(e))
                return
        rows = st.session_state.get("gl_rows")
        if rows is None:
            ids = st.session_state.get("gl_done") or []
            st.success("Added %s. They are listed under Knowledge base and used by the AI layer from the next review."
                       % ", ".join(ids) if ids else "Those passages were added.")
            st.caption("Upload another file to import more.")
            return
        for n in st.session_state.get("gl_notes", []):
            st.caption("Note: " + n)
        ticked = sum(1 for r in rows if r["use"])
        st.markdown("**%d passages found, %d ticked.** Change a title or text, untick what you do not want."
                    % (len(rows), ticked))
        edited = st.data_editor(
            pd.DataFrame(rows)[["use", "title", "text", "note"]], key="gl_editor", hide_index=True,
            width="stretch", num_rows="fixed",
            column_config={"use": st.column_config.CheckboxColumn("Add?", width="small"),
                           "title": st.column_config.TextColumn("Title", max_chars=guideline_import.MAX_TITLE),
                           "text": st.column_config.TextColumn("Passage text", max_chars=guideline_import.MAX_CHARS, width="large"),
                           "note": st.column_config.TextColumn("Note", disabled=True)})
        out = edited.to_dict("records")
        n_ticked = sum(1 for r in out if r["use"])
        if st.button("Add %d passage%s to the guidelines" % (n_ticked, "" if n_ticked == 1 else "s"),
                     type="primary", disabled=n_ticked == 0):
            try:
                ids = guideline_import.commit(out)
            except ValueError as e:
                st.error(str(e))
            else:
                db.log(None, admin_user, "Admin", "guidelines_imported", "%s: %s" % (up.name[:40], ", ".join(ids)))
                _forget_ai_answers()
                st.session_state.pop("gl_rows", None)
                st.session_state["gl_done"] = ids
                st.rerun()


def _brand_assets_tab(admin_user):
    store = assets.load_assets()
    a, b = st.columns(2, gap="large")
    with a:
        with st.container(border=True):
            st.markdown("#### Brand colours")
            st.markdown(_swatches(store["colours"]), unsafe_allow_html=True)
            st.caption("Image reviews compare uploaded images with these colours. The colours are also written into "
                       "guideline G5, so the rules and the AI read the same palette.")
            with st.form("colour_form", clear_on_submit=True):
                name = st.text_input("Colour name", max_chars=30, placeholder="for example: sage")
                code = st.color_picker("Pick the colour", value="#2E7D32")
                add = st.form_submit_button("Add colour")
            if add:
                try:
                    assets.add_colour(name, code)
                except ValueError as e:
                    st.error(str(e))
                else:
                    db.log(None, admin_user, "Admin", "colour_added", "%s %s" % (name.strip()[:30], code.upper()))
                    _forget_ai_answers()
                    st.success("Added. New image reviews use this colour.")
                    st.rerun()
            labels = {"%s  %s" % (c["name"], c["hex"].upper()): c["hex"] for c in store["colours"]}
            drop = st.multiselect("Remove colours", list(labels))
            if st.button("Remove selected", disabled=not drop):
                try:
                    assets.remove_colours([labels[d] for d in drop])
                except ValueError as e:
                    st.error(str(e))
                else:
                    db.log(None, admin_user, "Admin", "colour_removed", ", ".join(drop)[:80])
                    _forget_ai_answers()
                    st.rerun()
    with b:
        with st.container(border=True):
            st.markdown("#### Approved images")
            st.caption("Add logos and standard images with approved alt text. Creators can download them, and an "
                       "upload that is identical to one of these is recognised in the image review.")
            with st.form("image_form", clear_on_submit=True):
                f = st.file_uploader("Image (PNG, JPG or WEBP, up to 2 MB)", type=["png", "jpg", "jpeg", "webp"])
                iname = st.text_input("Name", max_chars=50, placeholder="for example: Leaf logo, green")
                ialt = st.text_input("Approved alt text", max_chars=250, placeholder="Describe what the image shows")
                iuse = st.text_input("Usage note (optional)", max_chars=200, placeholder="for example: keep clear space around it")
                add_i = st.form_submit_button("Add approved image")
            if add_i:
                if f is None:
                    st.warning("Choose an image first.")
                else:
                    try:
                        new_id = assets.add_image(iname, ialt, iuse, f.getvalue(), f.name)
                    except ValueError as e:
                        st.error(str(e))
                    else:
                        db.log(None, admin_user, "Admin", "image_added", "%s %s" % (new_id, iname.strip()[:40]))
                        st.success("Added %s." % new_id)
                        st.rerun()
            for img in store["images"]:
                c1, c2, c3 = st.columns([1, 3, 1])
                try:
                    c1.image(assets.image_bytes(img), width=90)
                except OSError:
                    c1.caption("(file missing)")
                c2.markdown("**%s** (%s)  \n%s" % (md_escape(img["name"]), img["id"], md_escape(img["alt"])))
                if c3.button("Remove", key="rmimg_" + img["id"]):
                    try:
                        assets.remove_image(img["id"])
                    except ValueError as e:
                        st.error(str(e))
                    else:
                        db.log(None, admin_user, "Admin", "image_removed", img["id"])
                        st.rerun()


def admin_view():
    admin_user = ROLE_INFO["Admin"]["user"]
    t1, t2, t_imp, t_ast, t3, t4 = st.tabs(
        ["Knowledge base", "Add to knowledge base", "Import guidelines", "Brand assets", "Activity log", "Insights"])
    with t_imp:
        _guideline_import_tab(admin_user)
    with t_ast:
        _brand_assets_tab(admin_user)

    with t1:
        with st.container(border=True):
            st.markdown("#### Brand guidelines")
            for p in load_guidelines():
                with st.expander("%s  %s" % (p["id"], p["title"])):
                    st.write(p["text"])
                    if p["id"] not in knowledge.CORE_IDS and st.button("Remove %s" % p["id"], key="rmg_" + p["id"]):
                        knowledge.remove_guideline(p["id"])
                        db.log(None, admin_user, "Admin", "guideline_removed", p["id"])
                        _forget_ai_answers()
                        st.rerun()
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
                fact_ok = 10 <= len(fact.strip()) <= 300
                dup = fact.strip().lower() in [f["fact"].strip().lower() for f in load_facts()]
                if ok and not fact_ok:
                    st.warning("Write a full statement between 10 and 300 characters.")
                elif ok and dup:
                    st.warning("This fact is already in the approved list.")
                elif ok:
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
                if ok2 and not (3 <= len(banned.strip()) <= 60 and 2 <= len(preferred.strip()) <= 60):
                    st.warning("Enter both terms (the term to avoid needs at least 3 characters, so it does not flag normal words).")
                elif ok2:
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

    with t4:
        from app.insights import render_insights

        render_insights("Admin", admin_user)