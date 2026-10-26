CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
h1, h2, h3 { letter-spacing: -0.02em; font-weight: 800; }
h1 { color: #1B4D2B; }
section[data-testid="stSidebar"] { border-right: 4px solid #2E7D32; }
.stButton > button, .stDownloadButton > button {
    border-radius: 10px; font-weight: 600; transition: all .15s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    transform: translateY(-1px); box-shadow: 0 4px 12px rgba(46,125,50,.25);
}
div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px; }
button[data-baseweb="tab"] { font-weight: 600; }
mark { border-radius: 6px; }
</style>
"""