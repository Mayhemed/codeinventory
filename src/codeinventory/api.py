from flask import Flask, jsonify, request
from flask_cors import CORS
from pathlib import Path
import yaml
from .database.db import InventoryDB

app = Flask(__name__)

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
CORS(app)

# Load configuration
config_path = Path(__file__).parent / 'config' / 'default.yaml'
with open(config_path) as f:
   config = yaml.safe_load(f)

def get_db_connection():
    """Create a new database connection for each request."""
    db_path = Path(config['database']['path']).expanduser()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/stats')
def get_stats():
   """Get overview statistics."""
   stats = {
       'total_tools': 0,
       'total_components': 0,
       'language_count': 0,
       'categories': {},
       'languages': {}
   }
   
   # Get all tools
   cursor = db.conn.cursor()
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
   
   return jsonify(stats)

@app.route('/api/tools')
def get_tools():
   """Get all tools."""
   cursor = db.conn.cursor()
   cursor.execute("SELECT * FROM tools ORDER BY name")
   tools = []
   
   for row in cursor.fetchall():
       tools.append(dict(row))
   
   return jsonify(tools)

@app.route('/api/components')
def get_components():
   """Get all components."""
   cursor = db.conn.cursor()
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

@app.route('/api/relationships')
def get_relationships():
   """Get tool relationships for visualization."""
   cursor = db.conn.cursor()
   
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
   
   # Get relationships for edges
   cursor.execute("""
       SELECT source_tool_id, target_tool_id, relationship_type
       FROM relationships
   """)
   
   edges = []
   for row in cursor.fetchall():
       edges.append({
           'source': row['source_tool_id'],
           'target': row['target_tool_id'],
           'relationship_type': row['relationship_type']
       })
   
   return jsonify({'nodes': nodes, 'edges': edges})

@app.route('/api/search')
def search():
   """Search tools."""
   query = request.args.get('q', '')
   if not query:
       return jsonify([])
   
   results = db.search(query)
   return jsonify(results)

if __name__ == '__main__':
   app.run(port=8000, debug=True)
