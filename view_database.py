import sqlite3
import json
import os
from pathlib import Path

DB_PATH = os.path.expanduser("~/.codeinventory/inventory.db")

def view_database():
    """View contents of the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Count tools
    cursor.execute("SELECT COUNT(*) FROM tools")
    tool_count = cursor.fetchone()[0]
    print(f"Total tools: {tool_count}")
    
    # Show some tools
    cursor.execute("""
        SELECT name, path, purpose, category, complexity 
        FROM tools 
        LIMIT 10
    """)
    
    print("\nFirst 10 tools:")
    for row in cursor.fetchall():
        name, path, purpose, category, complexity = row
        print(f"- {name}")
        print(f"  Path: {path}")
        print(f"  Purpose: {purpose}")
        print(f"  Category: {category}, Complexity: {complexity}")
        print()
    
    # Check dependencies
    cursor.execute("SELECT COUNT(*) FROM dependencies")
    dep_count = cursor.fetchone()[0]
    print(f"Total dependencies tracked: {dep_count}")
    
    conn.close()

if __name__ == "__main__":
    view_database()
