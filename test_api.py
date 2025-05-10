from flask import Flask, jsonify
import sqlite3
from pathlib import Path

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({"message": "API is running"})

@app.route('/api/tools')
def get_tools():
    try:
        db_path = Path("~/.codeinventory/inventory.db").expanduser()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tools")
        tools = cursor.fetchall()
        
        result = []
        for tool in tools:
            result.append(dict(tool))
        
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/stats')
def get_stats():
    try:
        db_path = Path("~/.codeinventory/inventory.db").expanduser()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.cursor()
        
        # Get total tools
        cursor.execute("SELECT COUNT(*) as total FROM tools")
        total = cursor.fetchone()['total']
        
        # Get language stats
        cursor.execute("SELECT language, COUNT(*) as count FROM tools GROUP BY language")
        languages = {}
        for row in cursor.fetchall():
            languages[row['language']] = row['count']
        
        conn.close()
        
        return jsonify({
            "total_tools": total,
            "languages": languages
        })
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(port=8000, debug=True)
