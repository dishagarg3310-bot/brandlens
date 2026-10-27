import streamlit as st

from app.style import CSS
from app.main_ui import main
from app.ui_extras import inject_css
inject_css()

main()
st.markdown(CSS, unsafe_allow_html=True)