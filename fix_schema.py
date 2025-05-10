import re

# Read the file
with open('/Users/markpiesner/Documents/GitHub/codeinventory/src/codeinventory/database/db.py', 'r') as f:
    content = f.read()

# Find the CREATE TABLE tools section
pattern = r'(CREATE TABLE IF NOT EXISTS tools \([^;]+created_at INTEGER DEFAULT \(strftime\(\'%s\', \'now\'\)\))'

# Replace with the new schema including all needed columns
replacement = r'''\1,
            execution_command TEXT,
            requires_args BOOLEAN,
            environment_vars TEXT,
            importable_items TEXT'''

# Make the replacement
new_content = re.sub(pattern, replacement, content)

# Write back to file
with open('/Users/markpiesner/Documents/GitHub/codeinventory/src/codeinventory/database/db.py', 'w') as f:
    f.write(new_content)

print("Schema updated successfully")
