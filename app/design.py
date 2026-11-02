"""Visual building blocks: hero banner and brand-health ring (one place for the look)."""
import html

import streamlit as st

CSS = """<style>
.bl-hero{border-radius:22px;padding:26px 30px;margin:0 0 16px;color:#fff;position:relative;
 overflow:hidden;box-shadow:0 14px 36px rgba(8,30,20,.28);
 background:radial-gradient(520px 230px at 92% -10%,var(--h1) 0%,rgba(0,0,0,0) 70%),
 linear-gradient(135deg,var(--h2) 0%,#0a1f17 100%)}
.bl-hero::after{content:"";position:absolute;right:-60px;top:-70px;width:240px;height:240px;
 border-radius:50%;background:rgba(255,255,255,.12)}
.bl-hero::before{content:"";position:absolute;right:90px;bottom:-90px;width:180px;height:180px;
 border-radius:50%;background:rgba(255,255,255,.08)}
.bl-hero h1{margin:6px 0 4px;padding:0;color:#fff;font-size:2rem;line-height:1.15;position:relative;z-index:1}
.bl-hero p{margin:0;opacity:.9;font-size:1rem;position:relative;z-index:1}
.bl-hero .row{display:flex;flex-wrap:wrap;gap:8px;position:relative;z-index:1}
.bl-hero .tag{padding:4px 13px;border-radius:999px;background:rgba(255,255,255,.2);
 font-weight:700;font-size:.8rem;backdrop-filter:blur(4px)}
.bl-ring{width:150px;height:150px;border-radius:50%;margin:4px auto 6px;display:grid;place-items:center;
 background:conic-gradient(var(--c) calc(var(--p) * 1%), rgba(128,128,128,.18) 0)}
.bl-ring-in{width:118px;height:118px;border-radius:50%;background:var(--secondary-background-color,#fff);
 display:flex;flex-direction:column;align-items:center;justify-content:center;
 box-shadow:inset 0 2px 8px rgba(0,0,0,.08)}
.bl-ring-in b{font-size:2.4rem;line-height:1;color:var(--c)}
.bl-ring-in span{font-size:.75rem;opacity:.65;margin-top:2px}
.bl-steps{display:flex;gap:10px;margin:0 0 16px;flex-wrap:wrap}
.bl-step{flex:1;min-width:150px;display:flex;align-items:center;gap:10px;padding:10px 14px;border-radius:14px;
 background:#fff;border:1px solid #dfe8dc;color:#7a887f;font-weight:600;font-size:.92rem}
.bl-step .n{width:28px;height:28px;border-radius:50%;display:grid;place-items:center;flex:none;
 background:#e6efe2;color:#4c5f52;font-weight:700;font-size:.85rem}
.bl-step.done{color:#2e7d32}.bl-step.done .n{background:#2e7d32;color:#fff}
.bl-step.now{color:#1f2a24;border-color:var(--c);box-shadow:0 0 0 3px rgba(46,125,50,.14)}
.bl-step.now .n{background:var(--c);color:#fff}
.bl-next{border-radius:14px;padding:12px 16px;margin:6px 0 12px;font-weight:600;color:#1b3a24;
 background:linear-gradient(90deg,#e8f5e9,#f4f9ee);border-left:5px solid #2e7d32}
.bl-next.wait{background:#e8f1fb;border-left-color:#1565c0;color:#0d2f57}
.bl-next.ok{background:#e6f4ea;border-left-color:#1b8a3a}
.bl-next small{display:block;font-weight:400;opacity:.8;margin-top:2px}
.bl-verdict{display:inline-block;margin-top:2px;padding:4px 14px;border-radius:999px;color:#fff;
 font-weight:700;font-size:.8rem;background:var(--c)}
</style>"""


def _darker(hex_color, f=0.62):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))


def hero(role, info, ai_label):
    c = info["color"]
    st.markdown(
        '<div class="bl-hero" style="--h1:%s;--h2:%s">'
        '<div class="row"><span class="tag">%s %s view</span>'
        '<span class="tag">%s</span><span class="tag">Humans decide</span></div>'
        "<h1>%s</h1><p>%s</p></div>"
        % (c, _darker(c), info["icon"], html.escape(role), html.escape(ai_label),
           html.escape(info["title"]), html.escape(info["tag"])),
        unsafe_allow_html=True,
    )


def ring(score, color, label):
    return (
        '<div class="bl-ring" style="--p:%d;--c:%s"><div class="bl-ring-in">'
        "<b>%d</b><span>out of 100</span></div></div>"
        '<div style="text-align:center"><span class="bl-verdict" style="--c:%s">%s</span></div>'
        % (score, color, score, color, html.escape(label))
    )


SPLASH = """<style>
@import url('https://fonts.googleapis.com/css2?family=Great+Vibes&display=swap');
.bl-splash{position:fixed;inset:0;z-index:2147483000;display:flex;flex-direction:column;align-items:center;
 justify-content:center;pointer-events:none;
 background:radial-gradient(900px 520px at 15% 10%,rgba(67,160,71,.55),transparent 60%),
 radial-gradient(800px 520px at 90% 90%,rgba(0,172,193,.45),transparent 60%),
 linear-gradient(135deg,#06150f 0%,#0b2a20 50%,#0a2630 100%);
 animation:bl-splash-out .8s ease 4.1s forwards}
.bl-splash svg{width:min(86vw,720px);height:auto;overflow:visible;filter:drop-shadow(0 0 22px rgba(120,255,190,.35))}
.bl-write{font-family:'Great Vibes','Brush Script MT','Segoe Script','Snell Roundhand',cursive;font-size:150px}
.bl-ink{fill:none;stroke:url(#blgrad);stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round;
 stroke-dasharray:2600;stroke-dashoffset:2600;
 animation:bl-draw 2.5s cubic-bezier(.45,.05,.35,1) .3s forwards,bl-inkout .6s ease 2.6s forwards}
.bl-fill{fill:url(#blgrad);stroke:none;opacity:0;animation:bl-fillin .9s ease 2.3s forwards}
.bl-splash-sub{margin-top:6px;font-size:1.05rem;letter-spacing:.14em;text-transform:uppercase;opacity:0;
 font-family:system-ui,-apple-system,"Segoe UI",sans-serif;
 background:linear-gradient(90deg,#d7ffe6,#8be9c6,#ffe9a8);-webkit-background-clip:text;background-clip:text;
 color:transparent;animation:bl-rise .8s ease 3.0s forwards}
@keyframes bl-draw{to{stroke-dashoffset:0}}
@keyframes bl-inkout{to{opacity:0}}
@keyframes bl-fillin{to{opacity:1}}
@keyframes bl-rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
@keyframes bl-splash-out{to{opacity:0;visibility:hidden}}
@media (prefers-reduced-motion:reduce){.bl-splash{display:none}}
</style>
<div class="bl-splash" aria-hidden="true">
 <svg viewBox="0 0 800 230" xmlns="http://www.w3.org/2000/svg">
  <defs><linearGradient id="blgrad" x1="0" y1="0" x2="1" y2="0.4">
   <stop offset="0" stop-color="#ffffff"/><stop offset=".45" stop-color="#9ff0c9"/><stop offset="1" stop-color="#ffe08a"/>
  </linearGradient></defs>
  <text class="bl-write bl-ink" x="400" y="150" text-anchor="middle">BrandLens</text>
  <text class="bl-write bl-fill" x="400" y="150" text-anchor="middle">BrandLens</text>
 </svg>
 <div class="bl-splash-sub">Catch it before you publish it</div>
</div>"""


def splash():
    """Handwriting-style welcome shown once per visit (like a phone's 'hello'), then it fades away."""
    if st.session_state.get("_splash_done"):
        return
    st.session_state["_splash_done"] = True
    st.markdown(SPLASH, unsafe_allow_html=True)


def stepper(steps, current, color="#2E7D32"):
    """A row of numbered steps: finished ones are ticked, the current one is highlighted."""
    parts = []
    for i, label in enumerate(steps):
        cls = "done" if i < current else ("now" if i == current else "")
        mark = "\u2713" if i < current else str(i + 1)
        parts.append('<div class="bl-step %s" style="--c:%s"><span class="n">%s</span>%s</div>'
                     % (cls, color, mark, html.escape(label)))
    st.markdown('<div class="bl-steps">%s</div>' % "".join(parts), unsafe_allow_html=True)


def next_step(text, hint="", kind=""):
    """One clear 'what to do now' box. Text is written by the app, never by users."""
    st.markdown('<div class="bl-next %s">%s%s</div>'
                % (kind, html.escape(text), "<small>%s</small>" % html.escape(hint) if hint else ""),
                unsafe_allow_html=True)


LOGIN_CSS = """<style>
.stApp,.stApp [data-testid="stAppViewContainer"],.stApp [data-testid="stMain"]{
 background:radial-gradient(900px 520px at 12% 8%,rgba(67,160,71,.38),transparent 60%),
 radial-gradient(800px 520px at 92% 92%,rgba(0,150,136,.32),transparent 60%),
 linear-gradient(135deg,#06150f 0%,#0b2a20 50%,#0a2630 100%)!important}
.stApp [data-testid="stHeader"]{background:transparent!important}
.bl-login-head{text-align:center;color:#fff;margin:1.2rem 0 1rem}
.bl-login-head .leaf{font-size:2.6rem}
.bl-login-head h1{color:#fff!important;margin:.1rem 0;font-size:2.6rem;letter-spacing:.01em}
.bl-login-head p{color:#b9d8c4!important;margin:0;font-size:1.02rem}
.bl-chips{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-top:12px}
.bl-chips span{padding:4px 12px;border-radius:999px;background:rgba(255,255,255,.10);
 border:1px solid rgba(255,255,255,.18);color:#dff3e4;font-size:.8rem}
.stApp div[data-testid="stVerticalBlockBorderWrapper"]{background:rgba(255,255,255,.09)!important;
 backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);border:1px solid rgba(255,255,255,.22)!important;
 border-radius:22px!important;box-shadow:0 24px 70px rgba(0,0,0,.45)!important}
.stApp h4,.stApp h3{color:#fff!important}
.stApp [data-testid="stMarkdownContainer"] p,.stApp [data-testid="stMarkdownContainer"] strong{color:#e3f4e8!important}
.stApp label p,.stApp [data-testid="stWidgetLabel"] p{color:#e3f4e8!important}
.stApp [data-testid="stCaptionContainer"],.stApp [data-testid="stCaptionContainer"] p{color:#d3e8d9!important;opacity:1!important}
.stApp [data-testid="stExpander"]{background:rgba(255,255,255,.07)!important;
 border:1px solid rgba(255,255,255,.20)!important;border-radius:16px!important;box-shadow:none!important}
.stApp [data-testid="stExpander"] details,.stApp [data-testid="stExpander"] summary{background:transparent!important}
.stApp [data-testid="stExpander"] summary,.stApp [data-testid="stExpander"] summary p,
.stApp [data-testid="stExpander"] summary span{color:#fff!important}
.stApp [data-testid="stExpander"] p,.stApp [data-testid="stExpander"] code{color:#e3f4e8!important}
.stApp [data-testid="stExpander"] code{background:rgba(255,255,255,.12)!important}
.stApp .stButton>button,.stApp .stFormSubmitButton>button{background:rgba(255,255,255,.12)!important;color:#fff!important;
 border:1px solid rgba(255,255,255,.30)!important;border-radius:12px!important;font-weight:600}
.stApp .stButton>button p{color:#fff!important}
.stApp .stButton>button:hover{background:rgba(255,255,255,.24)!important;border-color:#fff!important}
.stApp .stFormSubmitButton>button{background:linear-gradient(90deg,#43a047,#26a69a)!important;border:0!important}
.stApp .stFormSubmitButton>button p{color:#fff!important}
</style>"""