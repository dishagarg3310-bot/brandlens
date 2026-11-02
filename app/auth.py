"""Sign-in for the demo: each person has one account with one role.

Passwords are stored as salted PBKDF2-SHA256 hashes (never in plain text), compared in
constant time, and repeated wrong attempts lock the form for a minute. The demo
credentials are shown on the sign-in page on purpose so judges can try every role.
A production deployment would use single sign-on (SSO) instead of this demo list.
"""
import hashlib
import hmac
import time

import streamlit as st

ITERATIONS = 120000
MAX_FAILS = 5
LOCK_SECONDS = 60

# username -> (display role, salt, PBKDF2 hash)
ACCOUNTS = {
    "riya":  ("Creator",  "cebc3143a0c803c0", "fab7eee34a4d1a53e7fd929e0907b422628414bda40f86621ad37a6448bd8332"),
    "arjun": ("Manager",  "f62d9e000af7d0b2", "c0be90d7f4f6bebbb0f2ef20328600214a5902777d9db49c3d304d0de37742a6"),
    "meera": ("Reviewer", "8cc1b5f0df7c347f", "4ac55223c3e0cf50eafb6fb58d163c6833e91773ca4892e3172645b28b0fcde3"),
    "sana":  ("Admin",    "8298613e139ab539", "e3a62f2eaf1745fbdee5e25031aee3ef63aadd44b214f3678dfab78a95405189"),
}
DEMO_HINTS = [
    ("riya", "Creator@123", "Creator: writes drafts, fixes findings, submits"),
    ("arjun", "Manager@123", "Manager: approves or requests changes"),
    ("meera", "Reviewer@123", "Reviewer: verifies claims against approved facts"),
    ("sana", "Admin@123", "Admin: manages guidelines, facts, insights"),
]


def _hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS).hex()


def check(username, password):
    """Return the role if the credentials are right, else None."""
    acct = ACCOUNTS.get((username or "").strip().lower())
    # hash even for unknown users so timing does not reveal which usernames exist
    salt, good = (acct[1], acct[2]) if acct else ("0" * 16, "0" * 64)
    ok = hmac.compare_digest(_hash(password or "", salt), good)
    return acct[0] if (acct and ok) else None


def current():
    """(username, role) of the signed-in person, or None."""
    return st.session_state.get("auth")


def sign_out():
    for k in ("auth", "current_draft", "extra_findings", "upload_notes", "image_info"):
        st.session_state.pop(k, None)


ROLE_CARDS = [
    ("riya", "\u270D\uFE0F Creator", "Writes a draft, fixes the findings, submits it"),
    ("arjun", "\U0001F4CB Manager", "Approves a draft or asks for changes"),
    ("meera", "\U0001F50D Reviewer", "Checks risky claims against approved facts"),
    ("sana", "\u2699\uFE0F Admin", "Manages guidelines, facts and sees insights"),
]


def _sign_in(username, role):
    st.session_state["auth"] = (username, role)
    st.session_state["fails"] = 0
    st.rerun()


def require_login():
    """Show the sign-in page unless someone is signed in. Returns True when signed in."""
    if current():
        return True

    from app import design

    st.markdown(design.LOGIN_CSS, unsafe_allow_html=True)
    st.markdown(
        "<div class='bl-login-head'><div class='leaf'>\U0001F33F</div><h1>BrandLens</h1>"
        "<p>Catch it before you publish it. Every flag explained, every decision human.</p>"
        "<div class='bl-chips'><span>Checks tone, claims and accessibility</span>"
        "<span>Cites the rule behind every flag</span><span>You approve, AI only suggests</span></div></div>",
        unsafe_allow_html=True,
    )
    _, mid, _ = st.columns([1, 1.7, 1])
    with mid:
        with st.container(border=True):
            st.markdown("#### Pick a role to explore")
            st.caption("Demo accounts for a fictional brand (GreenLeaf Organics). No real data. "
                       "Suggested path: Creator, then Manager, then Reviewer, then Admin.")
            for row in (ROLE_CARDS[:2], ROLE_CARDS[2:]):
                cols = st.columns(2)
                for col, (u, label, what) in zip(cols, row):
                    with col:
                        if st.button(label, key="enter_" + u, use_container_width=True):
                            pw = [p for (name, p, _) in DEMO_HINTS if name == u][0]
                            _sign_in(u, check(u, pw))
                        st.caption(what)

        locked_until = st.session_state.get("locked_until", 0)
        wait = int(locked_until - time.time())
        with st.expander("Sign in with a username and password"):
            with st.form("login", clear_on_submit=False):
                user = st.text_input("Username")
                pw = st.text_input("Password", type="password")
                go = st.form_submit_button("Sign in", type="primary", use_container_width=True)
            if go:
                if wait > 0:
                    st.error("Too many attempts. Try again in %d seconds." % wait)
                else:
                    role = check(user, pw)
                    if role:
                        _sign_in(user.strip().lower(), role)
                    st.session_state["fails"] = st.session_state.get("fails", 0) + 1
                    if st.session_state["fails"] >= MAX_FAILS:
                        st.session_state["locked_until"] = time.time() + LOCK_SECONDS
                        st.session_state["fails"] = 0
                        st.error("Too many attempts. The form is locked for %d seconds." % LOCK_SECONDS)
                    else:
                        st.error("Wrong username or password.")
            st.caption("Accounts: " + ", ".join("`%s` / `%s`" % (u, p) for u, p, _ in DEMO_HINTS))
            st.caption("Passwords are stored as salted hashes. These demo credentials are public on purpose; "
                       "a real deployment would use single sign-on.")
    return False