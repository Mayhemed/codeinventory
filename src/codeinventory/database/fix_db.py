with open('db.py', 'r') as f:
    lines = f.readlines()

# Find the line with the issue and fix it
for i, line in enumerate(lines):
    if 'environment_vars = json.dumps(analysis.get' in line:
        # Add the None check before this line with proper indentation
        lines.insert(i, '        if analysis is None:\n')
        lines.insert(i+1, '            return None\n')
        break

# Write back
with open('db.py', 'w') as f:
    f.writelines(lines)

print("Fixed db.py indentation")
