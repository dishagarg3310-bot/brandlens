import streamlit as st

from app.theme import apply_theme

apply_theme()

from app import design

design.splash()   # shown straight away, before the heavier modules below are loaded

from app.style import CSS
from app.main_ui import main
from app.ui_extras import inject_css

inject_css()

main()
st.markdown(CSS, unsafe_allow_html=True)