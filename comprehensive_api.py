from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os
import json
from pathlib import Path
import shutil

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.expanduser("~/.codeinventory/inventory.db")
SETTINGS_PATH = os.path.expanduser("~/.codeinventory/settings.json")
DATA_DIR = os.path.expanduser("~/.codeinventory")

# Make sure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

def table_exists(conn, table_name):
    """Check if a table exists in the database."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None

# Load settings
def load_settings():
    """Load settings from file."""
    try:
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, 'r') as f:
                return json.load(f)
        else:
            # Default settings
            default_settings = {
                'exclusions': [],
                'directoryExclusions': []
            }
            # Create settings file with defaults
            with open(SETTINGS_PATH, 'w') as f:
                json.dump(default_settings, f, indent=2)
            return default_settings
    except Exception as e:
        print(f"Error loading settings: {e}")
        return {'exclusions': [], 'directoryExclusions': []}

# Save settings
def save_settings(settings):
    """Save settings to file."""
    try:
        with open(SETTINGS_PATH, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False

# Settings endpoints
@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get application settings."""
    try:
        settings = load_settings()
        return jsonify(settings)
    except Exception as e:
        print(f"Error in get_settings: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings/update', methods=['POST'])
def update_settings():
    """Update application settings."""
    try:
        data = request.json
        if not data or 'setting' not in data or 'value' not in data:
            return jsonify({'error': 'Invalid request data'}), 400
        
        settings = load_settings()
        
        # Update the specified setting
        setting_name = data['setting']
        setting_value = data['value']
        
        settings[setting_name] = setting_value
        
        # Save the updated settings
        success = save_settings(settings)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to save settings'}), 500
    except Exception as e:
        print(f"Error in update_settings: {e}")
        return jsonify({'error': str(e)}), 500

# Add file exclusion
@app.route('/api/exclusions/add', methods=['POST'])
def add_exclusion():
    """Add a file or directory to exclusions list."""
    try:
        data = request.json
        if not data or 'path' not in data:
            return jsonify({'error': 'Path is required'}), 400
        
        path = data['path']
        is_directory = data.get('isDirectory', False)
        include_subdirectories = data.get('includeSubdirectories', True)
        
        settings = load_settings()
        
        # Determine which exclusion list to update
        if is_directory:
            exclusion_entry = {
                'path': path,
                'includeSubdirectories': include_subdirectories
            }
            # Check if already exists
            if exclusion_entry not in settings.get('directoryExclusions', []):
                if 'directoryExclusions' not in settings:
                    settings['directoryExclusions'] = []
                settings['directoryExclusions'].append(exclusion_entry)
        else:
            # File exclusion
            if path not in settings.get('exclusions', []):
                if 'exclusions' not in settings:
                    settings['exclusions'] = []
                settings['exclusions'].append(path)
        
        # Save the updated settings
        success = save_settings(settings)
        
        if success:
            return jsonify({
                'success': True,
                'message': f"{'Directory' if is_directory else 'File'} added to exclusions"
            })
        else:
            return jsonify({'error': 'Failed to save exclusions'}), 500
    except Exception as e:
        print(f"Error in add_exclusion: {e}")
        return jsonify({'error': str(e)}), 500

# Remove file exclusion
@app.route('/api/exclusions/remove', methods=['POST'])
def remove_exclusion():
    """Remove a file or directory from exclusions list."""
    try:
        data = request.json
        if not data or 'path' not in data:
            return jsonify({'error': 'Path is required'}), 400
        
        path = data['path']
        is_directory = data.get('isDirectory', False)
        
        settings = load_settings()
        
        # Determine which exclusion list to update
        if is_directory:
            # Find the entry in directoryExclusions
            directory_exclusions = settings.get('directoryExclusions', [])
            for i, entry in enumerate(directory_exclusions):
                if entry.get('path') == path:
                    directory_exclusions.pop(i)
                    break
            settings['directoryExclusions'] = directory_exclusions
        else:
            # File exclusion
            if path in settings.get('exclusions', []):
                settings['exclusions'].remove(path)
        
        # Save the updated settings
        success = save_settings(settings)
        
        if success:
            return jsonify({
                'success': True,
                'message': f"{'Directory' if is_directory else 'File'} removed from exclusions"
            })
        else:
            return jsonify({'error': 'Failed to update exclusions'}), 500
    except Exception as e:
        print(f"Error in remove_exclusion: {e}")
        return jsonify({'error': str(e)}), 500

# Get file content
@app.route('/api/file-content', methods=['GET'])
def get_file_content():
    """Get the content of a file."""
    try:
        path = request.args.get('path')
        if not path:
            return jsonify({'error': 'Path parameter is required'}), 400
        
        # Normalize path
        file_path = os.path.expanduser(path)
        
        # Check if file exists
        if not os.path.isfile(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        return content
    except Exception as e:
        print(f"Error in get_file_content: {e}")
        return jsonify({'error': str(e)}), 500

# Check if path is excluded
@app.route('/api/exclusions/check', methods=['GET'])
def check_exclusion():
    """Check if a path is excluded."""
    try:
        path = request.args.get('path')
        if not path:
            return jsonify({'error': 'Path parameter is required'}), 400
        
        # Normalize path
        norm_path = os.path.normpath(path)
        
        settings = load_settings()
        file_exclusions = settings.get('exclusions', [])
        dir_exclusions = settings.get('directoryExclusions', [])
        
        # Check file exclusions
        if norm_path in file_exclusions:
            return jsonify({
                'excluded': True,
                'reason': 'File is explicitly excluded'
            })
        
        # Check directory exclusions
        for dir_ex in dir_exclusions:
            dir_path = os.path.normpath(dir_ex.get('path', ''))
            include_subdirs = dir_ex.get('includeSubdirectories', True)
            
            if include_subdirs:
                # Check if path is within excluded directory
                if norm_path.startswith(dir_path + os.sep) or norm_path == dir_path:
                    return jsonify({
                        'excluded': True,
                        'reason': f'Path is within excluded directory {dir_path}'
                    })
            else:
                # Check if path is directly in excluded directory (not in subdirectory)
                parent_dir = os.path.dirname(norm_path)
                if parent_dir == dir_path:
                    return jsonify({
                        'excluded': True,
                        'reason': f'Path is directly in excluded directory {dir_path}'
                    })
        
        return jsonify({'excluded': False})
    except Exception as e:
        print(f"Error in check_exclusion: {e}")
        return jsonify({'error': str(e)}), 500

# Get all exclusions
@app.route('/api/exclusions', methods=['GET'])
def get_exclusions():
    """Get all exclusions."""
    try:
        settings = load_settings()
        
        exclusions = {
            'files': settings.get('exclusions', []),
            'directories': settings.get('directoryExclusions', [])
        }
        
        return jsonify(exclusions)
    except Exception as e:
        print(f"Error in get_exclusions: {e}")
        return jsonify({'error': str(e)}), 500


def table_exists(conn, table_name):
    """Check if a table exists in the database."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None

# Stats route...
@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get database statistics."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        stats = {}
        
        # Get total tools
        cursor.execute("SELECT COUNT(*) FROM tools")
        stats['totalTools'] = cursor.fetchone()[0]
        
        # Get category breakdown
        cursor.execute("""
            SELECT category, COUNT(*) as count 
            FROM tools 
            WHERE category IS NOT NULL
            GROUP BY category
        """)
        stats['categories'] = dict(cursor.fetchall())
        
        # Get language breakdown
        cursor.execute("""
            SELECT language, COUNT(*) as count 
            FROM tools 
            WHERE language IS NOT NULL
            GROUP BY language
        """)
        stats['languages'] = dict(cursor.fetchall())
        
        # Get complexity breakdown
        cursor.execute("""
            SELECT complexity, COUNT(*) as count 
            FROM tools 
            WHERE complexity IS NOT NULL
            GROUP BY complexity
        """)
        stats['complexity'] = dict(cursor.fetchall())
        
        # Get recent scans
        cursor.execute("""
            SELECT name, path, last_analyzed 
            FROM tools 
            ORDER BY last_analyzed DESC 
            LIMIT 10
        """)
        recent_scans = []
        for row in cursor.fetchall():
            recent_scans.append({
                'name': row[0],
                'path': row[1],
                'timestamp': row[2]
            })
        stats['recentScans'] = recent_scans
        
        # Get function count
        cursor.execute("SELECT COUNT(*) FROM functions")
        stats['totalFunctions'] = cursor.fetchone()[0]
        
        # Get class count
        cursor.execute("SELECT COUNT(*) FROM classes")
        stats['totalClasses'] = cursor.fetchone()[0]
        
        # Get dependency count
        cursor.execute("SELECT COUNT(DISTINCT dependency) FROM dependencies")
        stats['totalDependencies'] = cursor.fetchone()[0]
        
        conn.close()
        return jsonify(stats)
    except Exception as e:
        print(f"Error in get_stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tools', methods=['GET'])
def get_tools():
    """Get all tools."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, path, purpose, category, complexity, language
            FROM tools
            ORDER BY name
        """)
        
        tools = []
        for row in cursor.fetchall():
            tools.append({
                'id': row[0],
                'name': row[1],
                'path': row[2],
                'purpose': row[3] or 'No description',
                'category': row[4] or 'unknown',
                'complexity': row[5] or 'unknown',
                'language': row[6] or 'unknown'
            })
        
        conn.close()
        return jsonify(tools)
    except Exception as e:
        print(f"Error in get_tools: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """Get project information."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Group tools by project directory
        cursor.execute("""
            SELECT path, name, category, language, complexity, purpose
            FROM tools
        """)
        
        projects = {}
        for row in cursor.fetchall():
            path = row[0]
            if '/' in path:
                project_name = path.split('/')[0]
            else:
                project_name = 'root'
                
            if project_name not in projects:
                projects[project_name] = {
                    'name': project_name,
                    'files': [],
                    'languages': set(),
                    'categories': set(),
                    'totalFiles': 0,
                    'complexFiles': 0
                }
            
            projects[project_name]['files'].append({
                'name': row[1],
                'path': row[0],
                'category': row[2] or 'unknown',
                'language': row[3] or 'unknown',
                'complexity': row[4] or 'unknown',
                'purpose': row[5] or ''
            })
            
            if row[3]:
                projects[project_name]['languages'].add(row[3])
            if row[2]:
                projects[project_name]['categories'].add(row[2])
            if row[4] == 'complex':
                projects[project_name]['complexFiles'] += 1
            
            projects[project_name]['totalFiles'] += 1
        
        # Convert sets to lists and calculate stats
        result = []
        for project in projects.values():
            project['languages'] = list(project['languages'])
            project['categories'] = list(project['categories'])
            result.append(project)
        
        conn.close()
        return jsonify(result)
    except Exception as e:
        print(f"Error in get_projects: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/insights', methods=['GET'])
def get_insights():
    """Get insights and analysis."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        insights = {
            'topDependencies': [],
            'complexityDistribution': {},
            'insights': [],
            'dependencyGraph': {'nodes': [], 'edges': []}
        }
        
        # Get top dependencies
        cursor.execute("""
            SELECT dependency, COUNT(*) as count
            FROM dependencies
            GROUP BY dependency
            ORDER BY count DESC
            LIMIT 15
        """)
        insights['topDependencies'] = [
            {'name': row[0], 'count': row[1]}
            for row in cursor.fetchall()
        ]
        
        # Get complexity distribution
        cursor.execute("""
            SELECT complexity, COUNT(*) as count
            FROM tools
            WHERE complexity IS NOT NULL
            GROUP BY complexity
        """)
        insights['complexityDistribution'] = dict(cursor.fetchall())
        
        # Generate insights based on data
        total_files = sum(insights['complexityDistribution'].values())
        complex_files = insights['complexityDistribution'].get('complex', 0)
        
        insights['insights'] = [
            {
                'type': 'info',
                'message': f'Your codebase contains {total_files} analyzed files'
            }
        ]
        
        if complex_files > 0:
            insights['insights'].append({
                'type': 'warning',
                'message': f'{complex_files} complex files may need refactoring'
            })
        
        # Build dependency graph
        cursor.execute("""
            SELECT t.id, t.name, t.path, d.dependency
            FROM tools t
            LEFT JOIN dependencies d ON t.id = d.tool_id
        """)
        
        nodes = {}
        edges = []
        
        for tool_id, name, path, dependency in cursor.fetchall():
            # Add node for the file
            if tool_id not in nodes:
                nodes[tool_id] = {
                    'id': tool_id,
                    'name': name,
                    'path': path,
                    'type': 'file'
                }
            
            # Add node for the dependency and edge
            if dependency:
                dep_id = f"dep_{dependency}"
                if dep_id not in nodes:
                    nodes[dep_id] = {
                        'id': dep_id,
                        'name': dependency,
                        'type': 'dependency'
                    }
                
                edges.append({
                    'source': tool_id,
                    'target': dep_id
                })
        
        insights['dependencyGraph'] = {
            'nodes': list(nodes.values()),
            'edges': edges
        }
        
        conn.close()
        return jsonify(insights)
    except Exception as e:
        print(f"Error in get_insights: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/file/<file_id>', methods=['GET'])
def get_file_details(file_id):
    """Get detailed information about a specific file."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get tool info
        cursor.execute("""
            SELECT id, name, path, purpose, description, category, complexity,
                   documentation, size, total_lines, code_lines, comment_lines
            FROM tools
            WHERE id = ?
        """, (file_id,))
        
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'File not found'}), 404
        
        file_info = {
            'id': row[0],
            'name': row[1],
            'path': row[2],
            'purpose': row[3],
            'description': row[4],
            'category': row[5],
            'complexity': row[6],
            'documentation': json.loads(row[7]) if row[7] else {},
            'size': row[8],
            'totalLines': row[9],
            'codeLines': row[10],
            'commentLines': row[11]
        }
        
        # Get functions
        cursor.execute("""
            SELECT name, args, returns, docstring, is_async, complexity
            FROM functions
            WHERE tool_id = ?
        """, (file_id,))
        
        functions = []
        for func_row in cursor.fetchall():
            functions.append({
                'name': func_row[0],
                'args': json.loads(func_row[1]) if func_row[1] else [],
                'returns': func_row[2],
                'docstring': func_row[3],
                'isAsync': bool(func_row[4]),
                'complexity': func_row[5]
            })
        file_info['functions'] = functions
        
        # Get classes
        cursor.execute("""
            SELECT name, bases, methods, attributes, docstring
            FROM classes
            WHERE tool_id = ?
        """, (file_id,))
        
        classes = []
        for class_row in cursor.fetchall():
            classes.append({
                'name': class_row[0],
                'bases': json.loads(class_row[1]) if class_row[1] else [],
                'methods': json.loads(class_row[2]) if class_row[2] else [],
                'attributes': json.loads(class_row[3]) if class_row[3] else [],
                'docstring': class_row[4]
            })
        file_info['classes'] = classes
        
        # Get dependencies
        cursor.execute("""
            SELECT dependency, import_type, line_number
            FROM dependencies
            WHERE tool_id = ?
        """, (file_id,))
        
        dependencies = []
        for dep_row in cursor.fetchall():
            dependencies.append({
                'dependency': dep_row[0],
                'importType': dep_row[1],
                'lineNumber': dep_row[2]
            })
        file_info['dependencies'] = dependencies
        
        conn.close()
        return jsonify(file_info)
    except Exception as e:
        print(f"Error in get_file_details: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/components', methods=['GET'])
def get_components():
    """Get component information (functions and classes)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        components = {
            'functions': [],
            'classes': []
        }
        
        # Get all functions with their parent file info
        cursor.execute("""
            SELECT f.name, f.docstring, f.is_async, f.complexity,
                   t.name as file_name, t.path as file_path, t.id as tool_id
            FROM functions f
            JOIN tools t ON f.tool_id = t.id
            ORDER BY f.name
        """)
        
        for row in cursor.fetchall():
            components['functions'].append({
                'name': row[0],
                'docstring': row[1],
                'isAsync': bool(row[2]),
                'complexity': row[3],
                'fileName': row[4],
                'filePath': row[5],
                'toolId': row[6]
            })
        
        # Get all classes with their parent file info
        cursor.execute("""
            SELECT c.name, c.docstring, c.is_dataclass,
                   t.name as file_name, t.path as file_path, t.id as tool_id
            FROM classes c
            JOIN tools t ON c.tool_id = t.id
            ORDER BY c.name
        """)
        
        for row in cursor.fetchall():
            components['classes'].append({
                'name': row[0],
                'docstring': row[1],
                'isDataclass': bool(row[2]),
                'fileName': row[3],
                'filePath': row[4],
                'toolId': row[5]
            })
        
        conn.close()
        return jsonify(components)
    except Exception as e:
        print(f"Error in get_components: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search', methods=['GET'])
def search():
    """Search across the codebase."""
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify([])
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        results = []
        
        # Search in tools (files)
        cursor.execute("""
            SELECT id, name, path, purpose, category
            FROM tools
            WHERE lower(name) LIKE ? OR lower(purpose) LIKE ? OR lower(path) LIKE ?
            LIMIT 20
        """, (f'%{query}%', f'%{query}%', f'%{query}%'))
        
        for row in cursor.fetchall():
            results.append({
                'type': 'file',
                'id': row[0],
                'name': row[1],
                'path': row[2],
                'description': row[3],
                'category': row[4]
            })
        
        # Search in functions
        cursor.execute("""
            SELECT f.name, f.docstring, t.name as file_name, t.path as file_path, t.id as tool_id
            FROM functions f
            JOIN tools t ON f.tool_id = t.id
            WHERE lower(f.name) LIKE ? OR lower(f.docstring) LIKE ?
            LIMIT 10
        """, (f'%{query}%', f'%{query}%'))
        
        for row in cursor.fetchall():
            results.append({
                'type': 'function',
                'name': row[0],
                'description': row[1],
                'fileName': row[2],
                'filePath': row[3],
                'toolId': row[4]
            })
        
        # Search in classes
        cursor.execute("""
            SELECT c.name, c.docstring, t.name as file_name, t.path as file_path, t.id as tool_id
            FROM classes c
            JOIN tools t ON c.tool_id = t.id
            WHERE lower(c.name) LIKE ? OR lower(c.docstring) LIKE ?
            LIMIT 10
        """, (f'%{query}%', f'%{query}%'))
        
        for row in cursor.fetchall():
            results.append({
                'type': 'class',
                'name': row[0],
                'description': row[1],
                'fileName': row[2],
                'filePath': row[3],
                'toolId': row[4]
            })
        
        conn.close()
        return jsonify(results)
    except Exception as e:
        print(f"Error in search: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print(f"Starting comprehensive API server on port 8001...")
    print(f"Database: {DB_PATH}")
    print(f"Settings: {SETTINGS_PATH}")
    
    # Check if database exists
    if os.path.exists(DB_PATH):
        print("Database found!")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        print(f"Available tables: {tables}")
    else:
        print("Warning: Database not found! Run the scanner first.")
    
    # Initialize settings if needed
    if not os.path.exists(SETTINGS_PATH):
        print("Creating default settings file...")
        save_settings({'exclusions': [], 'directoryExclusions': []})
    
    app.run(host='127.0.0.1', port=8001, debug=True)