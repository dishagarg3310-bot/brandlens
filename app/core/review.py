import time

import streamlit as st

from app.core import llm, rules
from app.core.knowledge import load_facts, load_glossary, load_guidelines

MAX_AI_PER_SESSION = 8


def review_text(text):
    passages = load_guidelines()
    glossary = load_glossary()
    facts = load_facts()
    found = rules.review_text(text, passages, glossary, facts)

    st.session_state["ai_status"] = "off"
    trace = {"status": "off", "reason": "no_key"}
    if llm.ai_available() and not st.session_state.get("use_ai", True):
        trace = {"status": "off", "reason": "switched_off"}
    if llm.ai_available() and st.session_state.get("use_ai", True):
        cache = st.session_state.setdefault("ai_cache", {})
        if text in cache:                          # same text again: instant, no second AI call
            found = found + [dict(f) for f in cache[text]["items"]]
            trace = dict(cache[text]["trace"], status="ok", cached=True)
            st.session_state["ai_status"] = "ok"
        elif st.session_state.get("ai_calls", 0) < MAX_AI_PER_SESSION:
            st.session_state["ai_calls"] = st.session_state.get("ai_calls", 0) + 1
            llm.last_trace = {}
            start = time.time()
            try:
                items = llm.review_with_llm(text, passages, facts, found)
                trace = dict(llm.last_trace or {}, status="ok", seconds=round(time.time() - start, 1))
                cache[text] = {"items": [dict(f) for f in items], "trace": trace}
                found = found + items
                st.session_state["ai_status"] = "ok"
            except Exception as e:  # never let the AI layer break a review
                print("AI layer error:", repr(e))
                trace = dict(llm.last_trace or {}, status="failed", seconds=round(time.time() - start, 1))
                st.session_state["ai_status"] = "failed"
            print("AI review took %.1fs" % (time.time() - start))
        else:
            trace = {"status": "limit"}
            st.session_state["ai_status"] = "limit"
    st.session_state["ai_trace"] = trace

    found.sort(key=lambda f: (f["span"] is None, f["span"][0] if f["span"] else 0))
    for i, f in enumerate(found, 1):
        f["id"] = "R%d" % i
    return found