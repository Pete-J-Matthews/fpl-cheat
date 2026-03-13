"""
CSS for FPL Cheat. Green + neutral theme, single content width, section cards, pill buttons.
"""

# Theme: green background, neutral text/surfaces, Premier League–style purple accent
FONT_DISPLAY = "Sora"
FONT_BODY = "Source Sans 3"


def get_app_css() -> str:
    """Return raw CSS."""
    return f"""
@import url('https://fonts.googleapis.com/css2?family={FONT_DISPLAY.replace(" ", "+")}:wght@400;500;600;700&family={FONT_BODY.replace(" ", "+")}:wght@400;500;600;700&display=swap');
:root{{
  --fpl-bg: #0d1f17;
  --fpl-bg-end: #132a1f;
  --fpl-surface: #1a2e24;
  --fpl-surface-elevated: #243d32;
  --fpl-text: #f5f4f0;
  --fpl-text-muted: rgba(245,244,240,0.7);
  --fpl-text-dim: rgba(245,244,240,0.5);
  --fpl-accent: #6b3a9e;
  --fpl-accent-hover: #7c4dab;
  --fpl-border: rgba(255,255,255,0.1);
  --fpl-border-subtle: rgba(255,255,255,0.06);
}}
header{{display:none !important;}}
section[data-testid="stHeader"],div[data-testid="stToolbar"],div[data-testid="stDecoration"]{{display:none !important;}}
#MainMenu,footer{{visibility:hidden !important;}}
.stApp{{background:var(--fpl-bg) !important;background-image:linear-gradient(180deg,var(--fpl-bg) 0%,var(--fpl-bg-end) 50%,var(--fpl-bg) 100%) !important;}}
.stApp .block-container{{max-width:900px;margin:0 auto;padding:1.5rem 1.25rem;box-sizing:border-box;}}
.stApp .app-header{{text-align:center;margin-bottom:1.5rem;}}
.stApp .app-header .logo-title{{display:inline-flex;align-items:center;justify-content:center;gap:14px;margin-bottom:0.5rem;}}
.stApp .app-header .logo-title img{{display:block;flex-shrink:0;}}
.stApp .app-header .logo-title h1{{font-family:'{FONT_DISPLAY}',sans-serif !important;font-size:2.75rem !important;letter-spacing:0.02em;margin:0;color:var(--fpl-text) !important;font-weight:600;}}
.stApp .app-header .tagline{{font-family:'{FONT_BODY}',system-ui,sans-serif !important;font-size:0.9rem;color:var(--fpl-text-muted);max-width:480px;margin:0 auto;line-height:1.5;}}
.stApp .section-card{{background:var(--fpl-surface);border:1px solid var(--fpl-border);border-radius:16px;padding:1.25rem 1.5rem;margin-bottom:1.25rem;}}
.stApp .section-card .section-title{{font-family:'{FONT_DISPLAY}',sans-serif !important;font-size:1.35rem !important;letter-spacing:0.02em;color:var(--fpl-text) !important;margin:0 0 1rem 0;font-weight:600;}}
.stApp h3,.stApp .stMarkdown h3,.stApp h2,.stApp .stMarkdown h2{{font-family:'{FONT_DISPLAY}',sans-serif !important;font-size:1.35rem !important;letter-spacing:0.02em;color:var(--fpl-text) !important;margin-top:0;margin-bottom:0.75rem;font-weight:600;}}
.stApp .block-container h1,.stApp .block-container h2,.stApp .block-container h3{{color:var(--fpl-text) !important;}}
.stApp [data-testid="stTextInput"]>div>div,.stApp [data-testid="stSelectbox"]>div>div{{background:var(--fpl-surface-elevated) !important;border:1px solid var(--fpl-border) !important;border-radius:12px !important;}}
.stApp [data-testid="stTextInput"]>div>div:focus-within,.stApp [data-testid="stSelectbox"]>div>div:focus-within{{border-color:var(--fpl-accent) !important;box-shadow:0 0 0 2px rgba(107,58,158,0.35) !important;}}
.stApp [data-testid="stTextInput"] input,.stApp [data-testid="stSelectbox"] input{{color:var(--fpl-text) !important;font-family:'{FONT_BODY}',system-ui,sans-serif !important;outline:none !important;}}
.stApp [data-testid="stTextInput"] input::placeholder{{color:var(--fpl-text-dim) !important;}}
.stApp [data-testid="stTextInput"] label,.stApp [data-testid="stSelectbox"] label{{color:var(--fpl-text) !important;font-family:'{FONT_BODY}',system-ui,sans-serif !important;}}
.stApp [data-testid="column"]:has([data-testid="stTextInput"]) + [data-testid="column"] [data-testid="stButton"] button:disabled{{background:var(--fpl-surface) !important;color:var(--fpl-text-dim) !important;border:1px solid var(--fpl-border-subtle) !important;cursor:not-allowed !important;}}
.stApp [data-testid="stButton"]>button[kind="primary"],.stApp [data-testid="stButton"]>button[data-testid="baseButton-primary"]{{background:var(--fpl-accent) !important;color:#f5f4f0 !important;font-family:'{FONT_BODY}',system-ui,sans-serif !important;font-weight:600 !important;border:none !important;border-radius:999px !important;padding:0.55rem 1.5rem !important;}}
.stApp [data-testid="stButton"]>button[kind="primary"]:hover,.stApp [data-testid="stButton"]>button[data-testid="baseButton-primary"]:hover{{background:var(--fpl-accent-hover) !important;}}
.stApp .section-card [data-testid="stButton"]>button[kind="secondary"],.stApp .section-card [data-testid="stButton"]>button:not([kind="primary"]){{background:var(--fpl-surface-elevated) !important;color:var(--fpl-text) !important;border:1px solid var(--fpl-border) !important;font-family:'{FONT_BODY}',system-ui,sans-serif !important;border-radius:999px !important;padding:0.5rem 1rem !important;}}
.stApp .section-card [data-testid="stButton"]>button[kind="secondary"]:hover,.stApp .section-card [data-testid="stButton"]>button:not([kind="primary"]):hover{{background:#2d4a3a !important;}}
.stApp .element-container{{margin-bottom:0.75rem;}}
.stApp .element-container:last-child{{margin-bottom:0;}}
.stApp .player-card{{width:100%;max-width:120px;margin:0 auto 2px auto;padding:6px;border:1px solid var(--fpl-border);border-radius:12px;background:var(--fpl-surface-elevated);text-align:center;}}
.stApp .player-card img{{height:35px;width:auto;display:block;margin:0 auto;}}
.team-comparison-section.team-comparison-section{{padding:1rem;}}
.team-comparison-row{{display:flex;gap:1rem;align-items:stretch;}}
.team-box{{flex:1;min-width:0;background:var(--fpl-surface);border:1px solid var(--fpl-border);border-radius:16px;padding:1rem;}}
.team-box-title,.team-box-bench,.team-box-placeholder{{color:var(--fpl-text);margin:0 0 0.5rem 0;font-size:0.9rem;font-family:'{FONT_BODY}',system-ui,sans-serif;}}
.team-box-placeholder{{color:var(--fpl-text-muted);font-size:0.85rem;}}
.pitch-row{{display:flex;flex-wrap:wrap;gap:0.5rem;margin-bottom:0.5rem;align-items:flex-start;justify-content:center;}}
.pitch-row:last-child{{margin-bottom:0;}}
.team-box .player-cell{{display:flex;flex-direction:column;align-items:center;flex-shrink:0;}}
.team-box .player-card--small{{max-width:72px;padding:4px;border-radius:8px;margin:0;text-align:center;background:var(--fpl-surface-elevated);border:1px solid var(--fpl-border);}}
.team-box .player-card--small img{{height:22px;width:auto;display:block;margin:0 auto;}}
.team-box .player-label{{margin:0 0 0.25rem 0;font-size:0.7rem;color:var(--fpl-text);font-weight:600;font-family:'{FONT_BODY}',system-ui,sans-serif;}}
.stApp [data-testid="stAlert"]{{background:var(--fpl-surface-elevated) !important;border:1px solid var(--fpl-border) !important;border-radius:12px !important;}}
.stApp p,.stApp span,.stApp div[data-testid="stMarkdown"]{{color:var(--fpl-text) !important;font-family:'{FONT_BODY}',system-ui,sans-serif !important;}}
.stApp .stCaption{{color:var(--fpl-text-muted) !important;font-size:0.8rem;}}
/* Similar Teams pills: similarity rating tight under pill, more space before Team Comparison */
.stApp .similarity-label{{color:var(--fpl-text-muted) !important;font-size:0.8rem !important;font-family:'{FONT_BODY}',system-ui,sans-serif !important;text-align:center !important;margin:0.1rem 0 0 0 !important;padding:0 !important;}}
.stApp [data-testid="column"]:has(.similarity-label) .element-container:first-child{{margin-bottom:0.1rem !important;}}
.stApp [data-testid="column"]:has(.similarity-label) .element-container:has(.similarity-label){{margin-bottom:1.5rem !important;}}
/* Similar Teams creator pills: purple on the button only (not the wrapper div). */
.stApp [class*="similar_teams_pills"] [data-testid="stButton"],.stApp [class*="similar-teams-pills"] [data-testid="stButton"]{{background:transparent !important;background-color:transparent !important;}}
.stApp [class*="similar_teams_pills"] [data-testid="stButton"]>*,.stApp [class*="similar-teams-pills"] [data-testid="stButton"]>*{{background:transparent !important;background-color:transparent !important;}}
.stApp [class*="similar_teams_pills"] button,.stApp [class*="similar-teams-pills"] button,.stApp [class*="similar_teams_pills"] button[data-testid="stBaseButton-secondary"],.stApp [class*="similar-teams-pills"] button[data-testid="stBaseButton-secondary"]{{background:rgba(107,58,158,0.45) !important;background-color:rgba(107,58,158,0.45) !important;color:var(--fpl-text) !important;border:1px solid var(--fpl-accent) !important;font-family:'{FONT_BODY}',system-ui,sans-serif !important;border-radius:999px !important;padding:0.5rem 1rem !important;}}
.stApp [class*="similar_teams_pills"] button:hover,.stApp [class*="similar-teams-pills"] button:hover,.stApp [class*="similar_teams_pills"] button[data-testid="stBaseButton-secondary"]:hover,.stApp [class*="similar-teams-pills"] button[data-testid="stBaseButton-secondary"]:hover{{background:rgba(107,58,158,0.55) !important;background-color:rgba(107,58,158,0.55) !important;border-color:var(--fpl-accent-hover) !important;}}
.stApp [class*="similar_teams_pills"] button *,.stApp [class*="similar-teams-pills"] button *{{background:transparent !important;background-color:transparent !important;}}
.stApp [class*="similar_teams_pills"] button[kind="primary"],.stApp [class*="similar_teams_pills"] button[data-testid="stBaseButton-primary"],.stApp [class*="similar-teams-pills"] button[kind="primary"],.stApp [class*="similar-teams-pills"] button[data-testid="stBaseButton-primary"]{{background:var(--fpl-accent) !important;background-color:var(--fpl-accent) !important;color:#f5f4f0 !important;border:2px solid rgba(245,244,240,0.9) !important;box-shadow:0 0 0 1px var(--fpl-accent) !important;font-weight:600 !important;}}
.stApp [class*="similar_teams_pills"] button[kind="primary"]:hover,.stApp [class*="similar_teams_pills"] button[data-testid="stBaseButton-primary"]:hover,.stApp [class*="similar-teams-pills"] button[kind="primary"]:hover,.stApp [class*="similar-teams-pills"] button[data-testid="stBaseButton-primary"]:hover{{background:var(--fpl-accent-hover) !important;border-color:rgba(245,244,240,0.95) !important;}}
.stApp .section-card [data-testid="column"]{{padding-left:0.35rem;padding-right:0.35rem;}}
"""


def get_app_styles() -> str:
    """Return HTML that injects app CSS via a data URI."""
    import base64
    css = get_app_css().strip()
    b64 = base64.b64encode(css.encode("utf-8")).decode("ascii")
    return f'<link rel="stylesheet" href="data:text/css;base64,{b64}">'
