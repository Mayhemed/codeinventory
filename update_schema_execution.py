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

# Add new columns for execution info
try:
    cursor.execute("ALTER TABLE tools ADD COLUMN execution_command TEXT")
    cursor.execute("ALTER TABLE tools ADD COLUMN requires_args BOOLEAN DEFAULT 0")
    cursor.execute("ALTER TABLE tools ADD COLUMN environment_vars TEXT")
    cursor.execute("ALTER TABLE tools ADD COLUMN importable_items TEXT")
except sqlite3.OperationalError as e:
    print(f"Column might already exist: {e}")

conn.commit()
conn.close()
print("Schema updated for execution info!")
