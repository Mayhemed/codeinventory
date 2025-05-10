import sqlite3
from pathlib import Path

# Adjust this path to your actual database location
db_path = Path("~/Documents/GitHub/LegalTools/inventory.db").expanduser()

# If database doesn't exist in LegalTools, check codeinventory directory
if not db_path.exists():
    db_path = Path("~/Documents/GitHub/codeinventory/inventory.db").expanduser()

if not db_path.exists():
    print(f"Database not found at {db_path}")
    # Create new database with correct schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE tools (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            language TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            purpose TEXT,
            description TEXT,
            category TEXT,
            complexity TEXT,
            last_modified INTEGER,
            last_analyzed INTEGER,
            created_at INTEGER DEFAULT (strftime('%s', 'now')),
            execution_command TEXT
        )
    """)
    conn.commit()
    conn.close()
    print(f"Created new database with execution_command column at {db_path}")
else:
    # Update existing database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(tools)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'execution_command' not in columns:
        cursor.execute("ALTER TABLE tools ADD COLUMN execution_command TEXT")
        conn.commit()
        print(f"Added execution_command column to existing database at {db_path}")
    else:
        print(f"execution_command column already exists in {db_path}")
    
    conn.close()
