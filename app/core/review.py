import streamlit as st

from app.core import llm, rules
from app.core.knowledge import load_facts, load_glossary, load_guidelines

MAX_AI_PER_SESSION = 8


def review_text(text):
    passages = load_guidelines()
    glossary = load_glossary()
    facts = load_facts()
    found = rules.review_text(text, passages, glossary, facts)

    if llm.ai_available():
        used = st.session_state.get("ai_calls", 0)
        if used < MAX_AI_PER_SESSION:
            st.session_state["ai_calls"] = used + 1
            try:
                found = found + llm.review_with_llm(text, passages, facts, found)
            except Exception as e:  # never let the AI layer break a review
                print("AI layer error:", repr(e))

    found.sort(key=lambda f: (f["span"] is None, f["span"][0] if f["span"] else 0))
    for i, f in enumerate(found, 1):
        f["id"] = "R%d" % i
    return found