import streamlit as st

PALETTE = "mint"   # mint | lavender | sand | ocean

PALETTES = {
    "mint":     dict(bg="#eaf5ee", bg2="#d6ecde", card="#f7fcf9", accent="#2e7d32", border="#bfdcc8"),
    "lavender": dict(bg="#f1eefb", bg2="#e2dcf7", card="#faf9ff", accent="#6d4ad8", border="#d6cdf3"),
    "sand":     dict(bg="#fbf3e6", bg2="#f3e4c9", card="#fffaf2", accent="#b4691f", border="#ecd9bb"),
    "ocean":    dict(bg="#e8f2fb", bg2="#d3e6f7", card="#f6faff", accent="#1f6fd1", border="#c3d9ef"),
}

CSS = """<style>
.stApp, [data-testid="stAppViewContainer"] {
  background: linear-gradient(160deg, __BG__ 0%, __BG2__ 100%) !important;
}
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebar"] {
  background: __BG2__ !important;
  border-right: 3px solid __ACCENT__ !important;
}
.stApp { --secondary-background-color: __CARD__; }
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stMetric"],
[data-testid="stExpander"] {
  background: __CARD__ !important;
  border: 1px solid __BORDER__ !important;
  border-radius: 16px !important;
  box-shadow: 0 2px 10px rgba(0,0,0,.06) !important;
}
[data-testid="stTabs"] button[aria-selected="true"] { color: __ACCENT__ !important; }
[data-testid="stTabs"] [data-baseweb="tab-highlight"] { background: __ACCENT__ !important; }
.stButton > button[kind="primary"], .stButton > button:hover {
  border-color: __ACCENT__ !important;
}
h1, h2, h3 { letter-spacing: -0.02em; }
</style>"""


def apply_theme():
    p = PALETTES.get(PALETTE, PALETTES["mint"])
    css = CSS
    for k, v in p.items():
        css = css.replace("__%s__" % k.upper(), v)
    st.markdown(css, unsafe_allow_html=True)
