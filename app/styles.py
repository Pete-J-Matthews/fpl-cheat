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
        .block-container { max-width: 1100px; margin: 0 auto; }
        /* Player card styling: consistent size, centered, bordered */
        .player-card {
            width: 100%;
            max-width: 120px;
            margin: 0 auto 6px auto;
            padding: 8px 6px;
            border: 1px solid rgba(255,255,255,0.18);
            border-radius: 12px;
            background: rgba(0,0,0,0.08);
            backdrop-filter: blur(2px);
            text-align: center;
        }
        .player-card img {
            height: 80px; /* uniform shirt size */
            width: auto;
            display: block;
            margin: 0 auto;
        }
        /* Center player labels under shirts */
        .element-container p, .element-container div, .element-container span { text-align: center; }
        
        /* Give columns a little bottom spacing */
        [data-testid="column"] { padding-bottom: 10px; }
        /* Make player cards breathe a bit */
        [data-testid="column"] div:has(img) { padding-bottom: 4px; }
        </style>
        """

