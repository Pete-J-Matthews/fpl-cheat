#!/usr/bin/env python3
"""
FPL Cheat - Local Development Setup
Simple setup script for local development environment.
"""

import sys
import sqlite3
import subprocess
from pathlib import Path


def check_prerequisites():
    """Check if Python and uv are available."""
    if sys.version_info < (3, 9):
        print("Error: Python 3.9+ required")
        sys.exit(1)
    
    try:
        subprocess.run(['uv', '--version'], check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Error: uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh")
        sys.exit(1)


def install_dependencies():
    """Install project dependencies."""
    try:
        subprocess.run(['uv', 'sync'], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to install dependencies: {e}")
        sys.exit(1)


def setup_database():
    """Create SQLite database with sample data."""
    db_path = "fpl_cheat.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS creator_teams (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            team_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_creator_teams_team_name ON creator_teams(team_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_creator_teams_user_name ON creator_teams(user_name)")
    
    # Add sample data
    sample_teams = [
        ('FPL General', 'General FPL'),
        ('FPL Focal', 'Focal FPL'),
        ('FPL Mate', 'FPL Mate'),
        ('FPL Team', 'FPL Team'),
        ('FPL Scout', 'FPL Scout'),
    ]
    
    cursor.executemany("INSERT OR IGNORE INTO creator_teams (user_name, team_name) VALUES (?, ?)", sample_teams)
    conn.commit()
    conn.close()


def setup_streamlit_config():
    """Create Streamlit configuration."""
    streamlit_dir = Path(".streamlit")
    streamlit_dir.mkdir(exist_ok=True)
    
    config_content = """[server]
headless = false
port = 8501
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false
"""
    
    config_file = streamlit_dir / "config.toml"
    config_file.write_text(config_content)


def main():
    """Main setup function."""
    print("Setting up FPL Cheat local development environment...")
    
    check_prerequisites()
    install_dependencies()
    setup_database()
    setup_streamlit_config()
    
    print("Setup complete!")
    print("Run: uv run streamlit run app.py")
    print("Open: http://localhost:8501")


if __name__ == "__main__":
    main()