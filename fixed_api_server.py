from flask import Flask, jsonify
from flask_cors import CORS
import sqlite3
import os
from pathlib import Path
import json

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.expanduser("~/.codeinventory/inventory.db")

def table_exists(conn, table_name):
    """Check if a table exists in the database."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get database statistics."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check what tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table'
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"Existing tables: {existing_tables}")
        
        stats = {}
        
        # Get total tools if table exists
        if 'tools' in existing_tables:
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
        else:
            stats['totalTools'] = 0
            stats['categories'] = {}
            stats['languages'] = {}
            stats['recentScans'] = []
        
        # Get function count if table exists
        if 'functions' in existing_tables:
            cursor.execute("SELECT COUNT(*) FROM functions")
            stats['totalFunctions'] = cursor.fetchone()[0]
        else:
            stats['totalFunctions'] = 0
        
        # Get class count if table exists
        if 'classes' in existing_tables:
            cursor.execute("SELECT COUNT(*) FROM classes")
            stats['totalClasses'] = cursor.fetchone()[0]
        else:
            stats['totalClasses'] = 0
        
        # Get dependency count if table exists
        if 'dependencies' in existing_tables:
            cursor.execute("SELECT COUNT(DISTINCT dependency) FROM dependencies")
            stats['totalDependencies'] = cursor.fetchone()[0]
        else:
            stats['totalDependencies'] = 0
        
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
        
        if not table_exists(conn, 'tools'):
            conn.close()
            return jsonify([])
        
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
        
        if not table_exists(conn, 'tools'):
            conn.close()
            return jsonify([])
        
        cursor = conn.cursor()
        
        # Group tools by project directory
        cursor.execute("""
            SELECT path, name, category, language
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
                    'categories': set()
                }
            
            projects[project_name]['files'].append({
                'name': row[1],
                'category': row[2] or 'unknown',
                'language': row[3] or 'unknown'
            })
            if row[3]:
                projects[project_name]['languages'].add(row[3])
            if row[2]:
                projects[project_name]['categories'].add(row[2])
        
        # Convert sets to lists and add file count
        result = []
        for project in projects.values():
            project['languages'] = list(project['languages'])
            project['categories'] = list(project['categories'])
            project['fileCount'] = len(project['files'])
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
        insights = {
            'topDependencies': [],
            'complexityDistribution': {},
            'insights': []
        }
        
        # Get dependency information if table exists
        if table_exists(conn, 'dependencies'):
            cursor = conn.cursor()
            cursor.execute("""
                SELECT dependency, COUNT(*) as count
                FROM dependencies
                GROUP BY dependency
                ORDER BY count DESC
                LIMIT 10
            """)
            insights['topDependencies'] = [
                {'name': row[0], 'count': row[1]}
                for row in cursor.fetchall()
            ]
        
        # Get complexity distribution if tools table exists
        if table_exists(conn, 'tools'):
            cursor = conn.cursor()
            cursor.execute("""
                SELECT complexity, COUNT(*) as count
                FROM tools
                WHERE complexity IS NOT NULL
                GROUP BY complexity
            """)
            insights['complexityDistribution'] = dict(cursor.fetchall())
            
            # Add insights based on data
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
        
        conn.close()
        return jsonify(insights)
    except Exception as e:
        print(f"Error in get_insights: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        # Check if database exists and is accessible
        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            return jsonify({
                'status': 'ok',
                'database': DB_PATH,
                'tables': tables
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Database not found',
                'database': DB_PATH
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    print(f"Starting API server on port 8001...")
    print(f"Database: {DB_PATH}")
    
    # Check if database exists
    if os.path.exists(DB_PATH):
        print("Database found!")
        # List tables
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        print(f"Available tables: {tables}")
    else:
        print("Warning: Database not found! Run the scanner first.")
    
    app.run(host='127.0.0.1', port=8001, debug=True)
