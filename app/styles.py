"""
CSS styling for the FPL Cheat app.
"""


def get_app_styles() -> str:
    """Return CSS styles for the app."""
    return """
        <style>
        .stApp {
            background: repeating-linear-gradient(
                0deg,
                #0b3e1d 0px,
                #0b3e1d 60px,
                #0e5226 60px,
                #0e5226 120px
            );
        }
        /* Constrain page width for better formation consistency */
        .block-container { max-width: 1100px; margin: 0 auto; padding-top: 3rem; padding-bottom: 1rem; }
        
        /* Prevent title clipping */
        h1 { margin-top: 1rem; margin-bottom: 1.5rem; }
        
        /* Reduce spacing between elements */
        .element-container { margin-bottom: 0.5rem; }
        [data-testid="stVerticalBlock"] > [style*="flex-direction: column"] > [data-testid="stVerticalBlock"] {
            padding-top: 0.5rem;
            padding-bottom: 0.5rem;
        }
        
        /* Player card styling: consistent size, centered, bordered */
        .player-card {
            width: 100%;
            max-width: 120px;
            margin: 0 auto 4px auto;
            padding: 6px 4px;
            border: 1px solid rgba(255,255,255,0.18);
            border-radius: 12px;
            background: rgba(0,0,0,0.08);
            backdrop-filter: blur(2px);
            text-align: center;
        }
        .player-card img {
            height: 35px; /* half size for compactness */
            width: auto;
            display: block;
            margin: 0 auto;
        }
        /* Center player labels under shirts */
        .element-container p, .element-container div, .element-container span { text-align: center; }
        
        /* Reduce column spacing */
        [data-testid="column"] { padding-bottom: 6px; padding-top: 0px; }
        [data-testid="column"] div:has(img) { padding-bottom: 2px; }
        
        /* Compact section headers */
        h3 { margin-top: 0.5rem; margin-bottom: 0.5rem; }
        
        /* Reduce spacing in pitch display */
        [data-testid="stVerticalBlock"] [data-testid="column"] {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
        
        /* Align inputs and buttons vertically */
        [data-testid="stTextInput"] > div > div,
        [data-testid="stNumberInput"] > div > div,
        [data-testid="stButton"] > button {
            margin-top: 0;
        }
        
        /* Ensure inputs align at top */
        [data-testid="column"] {
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
        }
        
        /* Align button with input fields - match label height */
        [data-testid="column"] [data-testid="stButton"] {
            margin-top: 1.75rem;
        }
        
        /* Consistent label positioning */
        [data-testid="stTextInput"] label,
        [data-testid="stNumberInput"] label {
            margin-bottom: 0.25rem;
        }
        
        /* Align captions consistently */
        [data-testid="column"] .stCaption {
            margin-top: 0.25rem;
            margin-bottom: 0;
        }
        
        /* Consistent label styling for manual labels */
        [data-testid="column"] p {
            margin-top: 0;
            font-size: 0.875rem;
        }
        
        /* Vertical divider between team columns */
        .team-divider {
            border-left: 2px solid rgba(255,255,255,0.4);
            height: 100vh;
            min-height: 500px;
            width: 2px;
        }
        [data-testid="column"]:has(.team-divider) {
            padding: 0;
            display: flex;
            align-items: stretch;
        }
        </style>
        """

