import ast
import pathlib
import shutil

FUNC = '''
def inject_css():
    st.markdown(
        """
<style>
.block-container { padding-top: 1.5rem; max-width: 1250px; }

[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e3e8df;
    border-left: 5px solid #2e7d32;
    border-radius: 14px;
    padding: 14px 18px;
    box-shadow: 0 2px 8px rgba(30, 60, 30, 0.06);
    transition: transform .15s ease, box-shadow .15s ease;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(30, 60, 30, 0.12);
}

textarea, input[type="text"] {
    border: 1.5px solid #b9cdb5 !important;
    border-radius: 10px !important;
    background: #ffffff !important;
}
textarea:focus, input[type="text"]:focus {
    border-color: #2e7d32 !important;
    box-shadow: 0 0 0 3px rgba(46, 125, 50, 0.15) !important;
}

.stButton > button {
    border-radius: 10px;
    font-weight: 600;
    border: 1.5px solid #2e7d32;
    transition: all .15s ease;
}
.stButton > button:hover {
    background: #2e7d32;
    color: #ffffff;
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(46, 125, 50, 0.25);
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2e7d32, #43a047);
    color: #ffffff;
    border: none;
}

[data-testid="stSidebar"] { border-right: 3px solid #2e7d32; }

[data-testid="stExpander"] {
    border-radius: 12px;
    border: 1px solid #dbe5d6;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
</style>
        """,
        unsafe_allow_html=True,
    )
'''

ui = pathlib.Path("app/ui_extras.py")
if not ui.exists():
    ui.write_text("import streamlit as st\n", encoding="utf-8")
text = ui.read_text(encoding="utf-8")
if "def inject_css" not in text:
    ui.write_text(text.rstrip() + "\n\n" + FUNC, encoding="utf-8")
    print("inject_css added to app/ui_extras.py")
else:
    print("inject_css already in ui_extras.py")

app = pathlib.Path("streamlit_app.py")
src = app.read_text(encoding="utf-8")
if "inject_css" in src:
    print("streamlit_app.py already calls inject_css. Nothing to do.")
else:
    shutil.copy(app, "streamlit_app.py.bak")
    tree = ast.parse(src)
    lines = src.splitlines(keepends=True)
    pos = None
    for node in tree.body:
        if (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                and getattr(node.value.func, "attr", "") == "set_page_config"):
            pos = node.end_lineno
            break
    if pos is None:
        print("set_page_config not found, adding after imports")
        pos = 0
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                pos = node.end_lineno
    if pos and not lines[pos - 1].endswith("\n"):
        lines[pos - 1] += "\n"
    lines.insert(pos, "from app.ui_extras import inject_css\ninject_css()\n")
    app.write_text("".join(lines), encoding="utf-8")
    print("streamlit_app.py updated (backup: streamlit_app.py.bak)")