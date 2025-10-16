"""
Database abstraction layer for FPL Cheat app.
Supports both SQLite (local development) and Supabase (production).
"""

import os
import sqlite3
from typing import Dict, List, Optional, Union
from abc import ABC, abstractmethod

try:
    from supabase import create_client, Client as SupabaseClient
except ImportError:
    SupabaseClient = None


class DatabaseInterface(ABC):
    """Abstract base class for database operations."""
    
    @abstractmethod
    def save_creator_team(self, user_name: str, team_name: str) -> bool:
        """Save a creator team to the database."""
        pass
    
    @abstractmethod
    def get_creator_teams(self) -> List[Dict]:
        """Get all creator teams from the database."""
        pass
    
    @abstractmethod
    def delete_creator_team(self, user_id: int) -> bool:
        """Delete a creator team by ID."""
        pass


class SQLiteDatabase(DatabaseInterface):
    """SQLite database implementation for local development."""
    
    def __init__(self, db_path: str = "fpl_cheat.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create creator_teams table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS creator_teams (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                team_name TEXT NOT NULL
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_creator_teams_team_name 
            ON creator_teams(team_name)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_creator_teams_user_name 
            ON creator_teams(user_name)
        """)
        
        conn.commit()
        conn.close()
    
    def save_creator_team(self, user_name: str, team_name: str) -> bool:
        """Save a creator team to SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO creator_teams (user_name, team_name)
                VALUES (?, ?)
            """, (user_name, team_name))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"SQLite error saving creator team: {e}")
            return False
    
    def get_creator_teams(self) -> List[Dict]:
        """Get all creator teams from SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM creator_teams")
            rows = cursor.fetchall()
            
            conn.close()
            
            # Convert Row objects to dictionaries
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"SQLite error fetching creator teams: {e}")
            return []
    
    def delete_creator_team(self, user_id: int) -> bool:
        """Delete a creator team by ID from SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM creator_teams WHERE user_id = ?", (user_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"SQLite error deleting creator team: {e}")
            return False


class SupabaseDatabase(DatabaseInterface):
    """Supabase database implementation for production."""
    
    def __init__(self, url: str, key: str):
        if SupabaseClient is None:
            raise ImportError("Supabase client not available. Install with: pip install supabase")
        
        self.client = create_client(url, key)
    
    def save_creator_team(self, user_name: str, team_name: str) -> bool:
        """Save a creator team to Supabase database."""
        try:
            result = self.client.table('creator_teams').insert({
                'user_name': user_name,
                'team_name': team_name
            }).execute()
            return True
        except Exception as e:
            print(f"Supabase error saving creator team: {e}")
            return False
    
    def get_creator_teams(self) -> List[Dict]:
        """Get all creator teams from Supabase database."""
        try:
            result = self.client.table('creator_teams').select('*').execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Supabase error fetching creator teams: {e}")
            return []
    
    def delete_creator_team(self, user_id: int) -> bool:
        """Delete a creator team by ID from Supabase database."""
        try:
            result = self.client.table('creator_teams').delete().eq('user_id', user_id).execute()
            return True
        except Exception as e:
            print(f"Supabase error deleting creator team: {e}")
            return False


def get_database() -> DatabaseInterface:
    """
    Factory function to get the appropriate database instance.
    Uses SQLite for local development, Supabase for production.
    """
    # Check if we're in production (Supabase secrets available)
    try:
        import streamlit as st
        
        # Check if Supabase secrets are available and valid
        if "supabase" in st.secrets:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
            
            # Check if secrets are properly configured (not placeholder values)
            if (url and key and 
                url != "your_supabase_project_url_here" and 
                key != "your_supabase_anon_key_here"):
                return SupabaseDatabase(url, key)
    except Exception:
        # If we can't access Streamlit secrets, fall back to SQLite
        pass
    
    # Default to SQLite for local development
    return SQLiteDatabase()


# Convenience functions for backward compatibility
def save_creator_team(db: DatabaseInterface, user_name: str, team_name: str) -> bool:
    """Save creator team using database interface."""
    return db.save_creator_team(user_name, team_name)


def get_creator_teams(db: DatabaseInterface) -> List[Dict]:
    """Get creator teams using database interface."""
    return db.get_creator_teams()


def delete_creator_team(db: DatabaseInterface, user_id: int) -> bool:
    """Delete creator team using database interface."""
    return db.delete_creator_team(user_id)
