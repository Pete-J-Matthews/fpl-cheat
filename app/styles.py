"""
CSS styling for the FPL Cheat app.
Returns raw CSS (no <style> tag) for injection via data URI to avoid Streamlit rendering it as text.
"""


def get_app_css() -> str:
    """Return raw CSS for the app. Use inject_styles() from app to inject via data URI."""
    return """
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@400;500;600;700&display=swap');
.stApp{background:#0f1419 !important;background-image:linear-gradient(180deg,#0f1419 0%,#131c28 50%,#0f1419 100%) !important;}
.stApp .block-container{max-width:1100px;margin:0 auto;padding-top:2rem;padding-bottom:2rem;}
.stApp .app-header{text-align:center;margin-bottom:2rem;}
.stApp .app-header .logo-title{display:inline-flex;align-items:center;justify-content:center;gap:14px;margin-bottom:0.5rem;}
.stApp .app-header .logo-title img{display:block;flex-shrink:0;}
.stApp .app-header .logo-title h1{font-family:'Bebas Neue',sans-serif !important;font-size:2.75rem !important;letter-spacing:0.04em;margin:0;color:#f5f5f4 !important;font-weight:400;}
.stApp .app-header .tagline{font-family:'DM Sans',system-ui,sans-serif !important;font-size:0.95rem;color:rgba(245,245,244,0.65);max-width:520px;margin:0 auto;line-height:1.5;}
.stApp h3,.stApp .stMarkdown h3,.stApp h2,.stApp .stMarkdown h2{font-family:'Bebas Neue',sans-serif !important;font-size:1.5rem !important;letter-spacing:0.03em;color:#f5f5f4 !important;margin-top:1.5rem;margin-bottom:0.75rem;}
.stApp h1,.stApp .stMarkdown h1{margin-top:0;margin-bottom:0;color:#f5f5f4 !important;}
.stApp .block-container h1,.stApp .block-container h2,.stApp .block-container h3{color:#f5f5f4 !important;}
.stApp .search-container{position:relative;width:100vw;left:50%;right:50%;margin-left:-50vw;margin-right:-50vw;padding-left:2rem;padding-right:2rem;box-sizing:border-box;}
.stApp [data-testid="stTextInput"]>div>div,.stApp [data-testid="stSelectbox"]>div>div{background:#232f3f !important;border:1px solid rgba(255,255,255,0.12) !important;border-radius:12px !important;}
.stApp [data-testid="stTextInput"] input,.stApp [data-testid="stSelectbox"] input{color:#f5f5f4 !important;font-family:'DM Sans',system-ui,sans-serif !important;}
.stApp [data-testid="stTextInput"] input::placeholder{color:rgba(245,245,244,0.5) !important;}
.stApp [data-testid="stTextInput"] label,.stApp [data-testid="stSelectbox"] label{color:rgba(245,245,244,0.9) !important;font-family:'DM Sans',system-ui,sans-serif !important;}
.stApp [data-testid="stButton"]>button[kind="primary"],.stApp [data-testid="stButton"]>button[data-testid="baseButton-primary"]{background:#e5a00d !important;color:#0f1419 !important;font-family:'DM Sans',system-ui,sans-serif !important;font-weight:600 !important;border:none !important;border-radius:12px !important;padding:0.6rem 1.25rem !important;}
.stApp [data-testid="stButton"]>button[kind="primary"]:hover,.stApp [data-testid="stButton"]>button[data-testid="baseButton-primary"]:hover{background:#f0b429 !important;}
.stApp [data-testid="stButton"]>button[kind="secondary"],.stApp [data-testid="stButton"]>button:not([kind="primary"]){background:#232f3f !important;color:#f5f5f4 !important;border:1px solid rgba(255,255,255,0.12) !important;font-family:'DM Sans',system-ui,sans-serif !important;border-radius:12px !important;}
.stApp .search-container [data-testid="column"]{max-width:none !important;}
.stApp .element-container{margin-bottom:0.5rem;}
.stApp .player-card{width:100%;max-width:120px;margin:0 auto 2px auto;padding:6px;border:1px solid rgba(255,255,255,0.1);border-radius:12px;background:#232f3f;text-align:center;}
.stApp .player-card img{height:35px;width:auto;display:block;margin:0 auto;}
.stApp .similar-teams-label{font-family:'DM Sans',system-ui,sans-serif;color:rgba(245,245,244,0.9);margin-bottom:0.5rem;}
.stApp .team-divider{border-left:2px solid rgba(255,255,255,0.12);height:100%;min-height:400px;}
.stApp [data-testid="stAlert"]{background:#232f3f !important;border:1px solid rgba(255,255,255,0.12) !important;border-radius:12px;}
.stApp p,.stApp span,.stApp div[data-testid="stMarkdown"]{color:rgba(245,245,244,0.9) !important;}
.stApp .stCaption{color:rgba(245,245,244,0.6) !important;}
"""


def get_app_styles() -> str:
    """Return HTML that injects app CSS via a data URI (avoids raw CSS being shown as text)."""
    import base64
    css = get_app_css().strip()
    b64 = base64.b64encode(css.encode("utf-8")).decode("ascii")
    return f'<link rel="stylesheet" href="data:text/css;base64,{b64}">'
