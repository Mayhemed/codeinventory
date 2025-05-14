import sqlite3
import os
from pathlib import Path

DB_PATH = os.path.expanduser("~/.codeinventory/inventory.db")

def migrate_database():
    """Add missing columns to the database."""
    print(f"Migrating database: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print("Database doesn't exist yet. Creating with new schema...")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check existing columns in tools table
    cursor.execute("PRAGMA table_info(tools)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    print(f"Existing columns: {existing_columns}")
    
    # Add missing columns
    if 'documentation' not in existing_columns:
        print("Adding 'documentation' column...")
        cursor.execute("ALTER TABLE tools ADD COLUMN documentation TEXT")
    
    # Ensure all enhanced tables exist
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS dependencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_id TEXT NOT NULL,
            dependency TEXT NOT NULL,
            FOREIGN KEY (tool_id) REFERENCES tools(id)
        );
        
        CREATE TABLE IF NOT EXISTS functions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_id TEXT NOT NULL,
            name TEXT NOT NULL,
            args TEXT,
            returns TEXT,
            docstring TEXT,
            FOREIGN KEY (tool_id) REFERENCES tools(id)
        );
        
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_id TEXT NOT NULL,
            name TEXT NOT NULL,
            bases TEXT,
            methods TEXT,
            docstring TEXT,
            FOREIGN KEY (tool_id) REFERENCES tools(id)
        );
    """)
    
    conn.commit()
    conn.close()
    print("Database migration complete!")

if __name__ == "__main__":
    migrate_database()
