import shutil

UI = "app/ui.py"
EX = "app/ui_extras.py"

NEW_BLOCK = '''    with tab_f:
        from app.ui_extras import SEV_LABEL, CAT_LABEL, sort_findings

        st.markdown(highlight(ver["content"], findings), unsafe_allow_html=True)
        if not findings:
            st.success("No issues found against the approved guidelines.")
        else:
            open_n = sum(1 for f in findings if f["status"] == "open")
            must_n = sum(1 for f in findings if f["severity"] == "high")
            st.caption("%d findings: %d must fix, %d waiting for your decision" % (len(findings), must_n, open_n))
        can_act = role == "Creator" and draft["status"] in EDITABLE
        DECISION = {"open": "Waiting for your decision", "accepted": "Accepted", "disputed": "Disputed"}
        for f in sort_findings([dict(x) for x in findings]):
            icon, sev = SEV_LABEL.get(f["severity"], ("🟡", "Small tweak"))
            cat = CAT_LABEL.get(f["category"], f["category"])
            with st.container(border=True):
                st.markdown("**%s %s: %s**%s" % (icon, sev, cat, "  `AI-suggested`" if f["source"] == "ai" else ""))
                if f["text"]:
                    st.markdown("❌ You wrote: `%s`" % f["text"])
                if f["suggestion"]:
                    st.markdown("✅ Try instead: **%s**" % f["suggestion"])
                why = f["message"] or ""
                if f["fact_id"]:
                    why += " Approved fact: %s" % f["fact_text"]
                st.markdown("💡 Why: %s" % why)
                st.caption("Rule: %s (%s)" % (f["rule_title"], f["rule_id"]))
                if can_act:
                    a, b, c = st.columns([1, 1, 2])
                    if a.button("Accept", key="acc%d" % f["id"]):
                        db.set_finding_status(f["id"], "accepted", user, role, did)
                        st.rerun()
                    if b.button("Dispute", key="dis%d" % f["id"]):
                        db.set_finding_status(f["id"], "disputed", user, role, did)
                        st.rerun()
                    c.write("Your decision: **%s**" % DECISION.get(f["status"], f["status"]))
                else:
                    st.write("Your decision: **%s**" % DECISION.get(f["status"], f["status"]))'''

EXTRAS = '''

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


def sort_findings(findings):
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(findings, key=lambda f: order.get(f.get("severity"), 3))
'''

with open(UI, encoding="utf-8") as fh:
    lines = fh.read().splitlines()

if lines[160].strip() != "with tab_f:" or 'st.write("Status: **%s**" % f["status"])' not in lines[188]:
    raise SystemExit("ABORT: line 161/189 match nahi hui. Kuch change nahi kiya.")

shutil.copy(UI, UI + ".bak")
lines[160:189] = NEW_BLOCK.split("\n")
with open(UI, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")

with open(EX, encoding="utf-8") as fh:
    ex = fh.read()
if "SEV_LABEL" not in ex:
    shutil.copy(EX, EX + ".bak")
    with open(EX, "a", encoding="utf-8") as fh:
        fh.write(EXTRAS)
    print("ui_extras.py updated")

print("DONE: app/ui.py patched (backup: app/ui.py.bak)")