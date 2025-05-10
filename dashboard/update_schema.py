import sqlite3
from pathlib import Path
import yaml

# Load configuration
config_path = Path('src/codeinventory/config/default.yaml')
with open(config_path) as f:
    config = yaml.safe_load(f)

db_path = Path(config['database']['path']).expanduser()
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Add new columns and tables for better organization
cursor.executescript("""
-- Add project/module grouping
ALTER TABLE tools ADD COLUMN project TEXT;
ALTER TABLE tools ADD COLUMN module TEXT;
ALTER TABLE tools ADD COLUMN parent_path TEXT;
ALTER TABLE tools ADD COLUMN is_entry_point BOOLEAN DEFAULT 0;

-- Create table for file relationships
CREATE TABLE IF NOT EXISTS file_relationships (
    id TEXT PRIMARY KEY,
    source_file_id TEXT NOT NULL,
    target_file_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL, -- imports, extends, implements, uses
    line_number INTEGER,
    FOREIGN KEY (source_file_id) REFERENCES tools(id),
    FOREIGN KEY (target_file_id) REFERENCES tools(id)
);

-- Create table for projects/modules
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    description TEXT,
    type TEXT, -- application, library, script, module
    language TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

conn.commit()
conn.close()
print("Schema updated successfully!")
