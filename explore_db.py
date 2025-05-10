#!/usr/bin/env python
import sqlite3
from pathlib import Path

db_path = Path("~/.codeinventory/inventory.db").expanduser()
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# Get all tools
cursor = conn.cursor()
cursor.execute("SELECT * FROM tools ORDER BY name")
tools = cursor.fetchall()

print(f"Found {len(tools)} tools in the database:\n")

for tool in tools:
    print(f"Name: {tool['name']}")
    print(f"Purpose: {tool['purpose']}")
    print(f"Category: {tool['category']}")
    print(f"Language: {tool['language']}")
    print("-" * 50)

# Get statistics
cursor.execute("SELECT language, COUNT(*) as count FROM tools GROUP BY language")
stats = cursor.fetchall()

print("\nLanguage Statistics:")
for stat in stats:
    print(f"{stat['language']}: {stat['count']} files")

conn.close()
