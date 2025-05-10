from flask import Flask, jsonify, request
from flask_cors import CORS
from pathlib import Path
import yaml
import sqlite3
import json

app = Flask(__name__)
CORS(app)

# Load configuration
config_path = Path(__file__).parent / 'src' / 'codeinventory' / 'config' / 'default.yaml'
with open(config_path) as f:
    config = yaml.safe_load(f)

def get_db_connection():
    """Create a new database connection for each request."""
    db_path = Path(config['database']['path']).expanduser()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    """API root endpoint."""
    return jsonify({
        'message': 'CodeInventory API',
        'version': '1.0.0',
        'endpoints': {
            '/api/stats': 'Get overview statistics',
            '/api/tools': 'Get all tools',
            '/api/components': 'Get all components',
            '/api/relationships': 'Get tool relationships for visualization',
            '/api/search?q=<query>': 'Search tools'
        }
    })

@app.route('/api/stats')
def get_stats():
    """Get overview statistics."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    stats = {
        'total_tools': 0,
        'total_components': 0,
        'language_count': 0,
        'categories': {},
        'languages': {}
    }
    
    try:
        # Get all tools
        cursor.execute("SELECT * FROM tools")
        tools = cursor.fetchall()
        
        stats['total_tools'] = len(tools)
        
        # Count by category and language
        for tool in tools:
            category = tool['category'] or 'Uncategorized'
            language = tool['language']
            
            stats['categories'][category] = stats['categories'].get(category, 0) + 1
            stats['languages'][language] = stats['languages'].get(language, 0) + 1
        
        stats['language_count'] = len(stats['languages'])
        
        # Count components
        cursor.execute("SELECT COUNT(*) FROM components")
        stats['total_components'] = cursor.fetchone()[0]
        
    finally:
        conn.close()
    
    return jsonify(stats)

@app.route('/api/tools')
def get_tools():
    """Get all tools."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM tools ORDER BY name")
        tools = []
        
        for row in cursor.fetchall():
            tool = dict(row)
            # Parse JSON fields
            if tool.get('environment_vars'):
                tool['environment_vars'] = json.loads(tool['environment_vars'])
            if tool.get('importable_items'):
                tool['importable_items'] = json.loads(tool['importable_items'])
            tools.append(tool)
        
        return jsonify(tools)
    finally:
        conn.close()

@app.route('/api/components')
def get_components():
    """Get all components."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT c.*, t.name as tool_name
            FROM components c
            JOIN tools t ON c.tool_id = t.id
            ORDER BY c.name
        """)
        
        components = []
        for row in cursor.fetchall():
            components.append(dict(row))
        
        return jsonify(components)
    finally:
        conn.close()

@app.route('/api/relationships')
def get_relationships():
    """Get tool relationships for visualization."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get all tools for nodes
        cursor.execute("SELECT id, name, category, purpose FROM tools")
        nodes = []
        for row in cursor.fetchall():
            nodes.append({
                'id': row['id'],
                'name': row['name'],
                'category': row['category'] or 'Uncategorized',
                'purpose': row['purpose']
            })
        
        # Get relationships for edges (empty for now)
        edges = []
        
        return jsonify({'nodes': nodes, 'edges': edges})
    finally:
        conn.close()

@app.route('/api/search')
def search():
    """Search tools."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify([])
        
        cursor.execute("""
            SELECT * FROM tools 
            WHERE name LIKE ? OR purpose LIKE ? OR description LIKE ?
            ORDER BY name
        """, (f'%{query}%', f'%{query}%', f'%{query}%'))
        
        results = []
        for row in cursor.fetchall():
            results.append(dict(row))
        
        return jsonify(results)
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(port=8001, debug=True)
