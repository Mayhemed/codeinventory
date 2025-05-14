import os
import json
import time
import sqlite3
import hashlib
import requests
from pathlib import Path
from datetime import datetime
import re
import ast

# Configuration
OLLAMA_HOST = "http://localhost:11434"
MODEL = "codellama"
DB_PATH = os.path.expanduser("~/.codeinventory/inventory.db")
TIMEOUT = 30

class CodeAnalyzer:
    def __init__(self):
        self.imports = []
        self.functions = []
        self.classes = []
        self.global_vars = []
        self.dependencies = set()
    
    def analyze_python_code(self, code):
        """Extract detailed information from Python code."""
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.imports.append({
                            'type': 'import',
                            'module': alias.name,
                            'alias': alias.asname
                        })
                        self.dependencies.add(alias.name.split('.')[0])
                        
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        self.imports.append({
                            'type': 'from',
                            'module': module,
                            'name': alias.name,
                            'alias': alias.asname
                        })
                        if module:
                            self.dependencies.add(module.split('.')[0])
                
                elif isinstance(node, ast.FunctionDef):
                    func_info = {
                        'name': node.name,
                        'args': [],
                        'returns': None,
                        'decorators': [ast.unparse(d) for d in node.decorator_list] if hasattr(ast, 'unparse') else [],
                        'docstring': ast.get_docstring(node),
                        'is_async': isinstance(node, ast.AsyncFunctionDef)
                    }
                    
                    # Extract arguments
                    for arg in node.args.args:
                        arg_info = {'name': arg.arg, 'type': None}
                        if arg.annotation:
                            try:
                                arg_info['type'] = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation)
                            except:
                                pass
                        func_info['args'].append(arg_info)
                    
                    # Extract return type
                    if node.returns:
                        try:
                            func_info['returns'] = ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)
                        except:
                            pass
                    
                    self.functions.append(func_info)
                
                elif isinstance(node, ast.ClassDef):
                    class_info = {
                        'name': node.name,
                        'bases': [],
                        'methods': [],
                        'attributes': [],
                        'docstring': ast.get_docstring(node)
                    }
                    
                    # Extract base classes
                    for base in node.bases:
                        try:
                            class_info['bases'].append(ast.unparse(base) if hasattr(ast, 'unparse') else str(base))
                        except:
                            pass
                    
                    # Extract methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_info = {
                                'name': item.name,
                                'args': [arg.arg for arg in item.args.args],
                                'is_async': isinstance(item, ast.AsyncFunctionDef),
                                'docstring': ast.get_docstring(item)
                            }
                            class_info['methods'].append(method_info)
                        elif isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name):
                                    class_info['attributes'].append(target.id)
                    
                    self.classes.append(class_info)
                
                elif isinstance(node, ast.Assign) and node.col_offset == 0:
                    # Global variables
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self.global_vars.append(target.id)
        
        except Exception as e:
            print(f"AST parsing error: {e}")
        
        return {
            'imports': self.imports,
            'functions': self.functions,
            'classes': self.classes,
            'global_vars': self.global_vars,
            'dependencies': list(self.dependencies)
        }

def get_file_info(filepath):
    """Get basic file information."""
    stats = filepath.stat()
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    return {
        'path': str(filepath),
        'name': filepath.name,
        'type': 'module',
        'language': get_language(filepath),
        'content': content,
        'hash': hashlib.md5(content.encode()).hexdigest(),
        'size': stats.st_size,
        'last_modified': int(stats.st_mtime * 1000)
    }

def get_language(filepath):
    """Determine file language from extension."""
    ext = filepath.suffix.lower()
    mapping = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.sh': 'shell',
        '.bash': 'shell'
    }
    return mapping.get(ext, 'unknown')

def analyze_with_ollama(file_info, structure_info):
    """Get high-level analysis from Ollama."""
    prompt = f"""Analyze this {file_info['language']} code and provide insights:

File: {file_info['name']}
Imports: {len(structure_info.get('imports', []))} imports
Functions: {len(structure_info.get('functions', []))} functions
Classes: {len(structure_info.get('classes', []))} classes
Dependencies: {', '.join(structure_info.get('dependencies', []))}

Code snippet:
{file_info['content'][:2000]}

Provide a JSON response with:
- purpose: What this code does (be specific)
- description: Detailed explanation
- category: file-ops, api, ui, data-processing, utility, build, test, config
- complexity: simple, moderate, complex
- main_functionality: List of main features
- potential_issues: Any potential problems or improvements
- usage_examples: How to use this code

Respond with valid JSON only."""

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "temperature": 0.3,
                "stream": False
            },
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get('response', '{}')
            # Extract JSON from response
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                return json.loads(match.group())
    except Exception as e:
        print(f" Ollama error: {e}")
    
    return None

def generate_documentation(file_info, structure_info, ollama_analysis):
    """Generate comprehensive documentation."""
    doc = {
        'file': file_info['name'],
        'path': file_info['path'],
        'language': file_info['language'],
        'last_analyzed': datetime.now().isoformat(),
        'structure': structure_info,
        'analysis': ollama_analysis or {},
        'documentation': {
            'summary': ollama_analysis.get('purpose', 'Unknown') if ollama_analysis else 'Unknown',
            'description': ollama_analysis.get('description', '') if ollama_analysis else '',
            'category': ollama_analysis.get('category', 'unknown') if ollama_analysis else 'unknown',
            'complexity': ollama_analysis.get('complexity', 'unknown') if ollama_analysis else 'unknown'
        }
    }
    
    # Add dependency graph information
    doc['dependency_graph'] = {
        'imports': structure_info.get('imports', []),
        'dependencies': structure_info.get('dependencies', []),
        'exported': {
            'functions': [f['name'] for f in structure_info.get('functions', [])],
            'classes': [c['name'] for c in structure_info.get('classes', [])],
            'variables': structure_info.get('global_vars', [])
        }
    }
    
    return doc

def init_db():
    """Initialize the database with enhanced schema."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create enhanced tables
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS tools (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            language TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            purpose TEXT,
            description TEXT,
            category TEXT,
            complexity TEXT,
            last_modified INTEGER,
            last_analyzed INTEGER,
            created_at INTEGER DEFAULT (strftime('%s', 'now')),
            documentation TEXT
        );
        
        CREATE TABLE IF NOT EXISTS dependencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_id TEXT NOT NULL,
            dependency TEXT NOT NULL,
            FOREIGN KEY (tool_id) REFERENCES tools(id)
        );
        
        CREATE TABLE IF NOT EXISTS functions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_id TEXT NOT NULL,
            name TEXT NOT NULL,
            args TEXT,
            returns TEXT,
            docstring TEXT,
            FOREIGN KEY (tool_id) REFERENCES tools(id)
        );
        
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_id TEXT NOT NULL,
            name TEXT NOT NULL,
            bases TEXT,
            methods TEXT,
            docstring TEXT,
            FOREIGN KEY (tool_id) REFERENCES tools(id)
        );
    """)
    
    conn.commit()
    return conn

def save_to_db(conn, file_info, structure_info, ollama_analysis, documentation):
    """Save enhanced analysis to database."""
    cursor = conn.cursor()
    timestamp = int(datetime.now().timestamp() * 1000)
    tool_id = file_info['hash']
    
    try:
        # Save main tool info
        cursor.execute("""
            INSERT OR REPLACE INTO tools (
                id, path, name, type, language, file_hash,
                purpose, description, category, complexity,
                last_modified, last_analyzed, documentation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tool_id,
            file_info['path'],
            file_info['name'],
            file_info['type'],
            file_info['language'],
            file_info['hash'],
            documentation['documentation']['summary'],
            documentation['documentation']['description'],
            documentation['documentation']['category'],
            documentation['documentation']['complexity'],
            file_info['last_modified'],
            timestamp,
            json.dumps(documentation)
        ))
        
        # Save dependencies
        cursor.execute("DELETE FROM dependencies WHERE tool_id = ?", (tool_id,))
        for dep in structure_info.get('dependencies', []):
            cursor.execute("""
                INSERT INTO dependencies (tool_id, dependency)
                VALUES (?, ?)
            """, (tool_id, dep))
        
        # Save functions
        cursor.execute("DELETE FROM functions WHERE tool_id = ?", (tool_id,))
        for func in structure_info.get('functions', []):
            cursor.execute("""
                INSERT INTO functions (tool_id, name, args, returns, docstring)
                VALUES (?, ?, ?, ?, ?)
            """, (
                tool_id,
                func['name'],
                json.dumps(func.get('args', [])),
                func.get('returns'),
                func.get('docstring')
            ))
        
        # Save classes
        cursor.execute("DELETE FROM classes WHERE tool_id = ?", (tool_id,))
        for cls in structure_info.get('classes', []):
            cursor.execute("""
                INSERT INTO classes (tool_id, name, bases, methods, docstring)
                VALUES (?, ?, ?, ?, ?)
            """, (
                tool_id,
                cls['name'],
                json.dumps(cls.get('bases', [])),
                json.dumps(cls.get('methods', [])),
                cls.get('docstring')
            ))
        
        conn.commit()
        return True
    except Exception as e:
        print(f" DB error: {e}")
        conn.rollback()
        return False

def analyze_project_structure(root_path):
    """Analyze overall project structure."""
    project_info = {
        'name': root_path.name,
        'path': str(root_path),
        'modules': [],
        'entry_points': [],
        'total_files': 0,
        'languages': {},
        'dependencies': set()
    }
    
    # Look for common entry points
    entry_point_names = ['main.py', 'app.py', 'run.py', 'start.py', '__main__.py', 
                        'index.js', 'server.js', 'index.html']
    
    for entry in entry_point_names:
        entry_path = root_path / entry
        if entry_path.exists():
            project_info['entry_points'].append(str(entry_path))
    
    # Look for setup files
    setup_files = ['setup.py', 'pyproject.toml', 'package.json', 'requirements.txt', 'Pipfile']
    for setup in setup_files:
        setup_path = root_path / setup
        if setup_path.exists():
            project_info['modules'].append({
                'type': 'setup',
                'path': str(setup_path),
                'name': setup
            })
    
    return project_info

def main():
    # Initialize database
    conn = init_db()
    
    # Define directories to scan
    scan_dirs = ['rag', 'ai_analysis', 'newClient', 'OpenManus']
    extensions = ['.py', '.js', '.jsx', '.sh']
    
    all_projects = {}
    
    # Analyze each project directory
    for dir_name in scan_dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            continue
        
        print(f"\nAnalyzing project: {dir_name}")
        project_info = analyze_project_structure(dir_path)
        all_projects[dir_name] = project_info
        
        files = []
        for ext in extensions:
            found_files = [f for f in dir_path.rglob(f"*{ext}") 
                         if '.venv' not in str(f) and 'venv' not in str(f) 
                         and '__pycache__' not in str(f)]
            files.extend(found_files)
        
        print(f"Found {len(files)} files to analyze")
        project_info['total_files'] = len(files)
        
        for i, filepath in enumerate(files):
            print(f"[{i+1}/{len(files)}] {filepath.name}...", end='', flush=True)
            
            try:
                file_info = get_file_info(filepath)
                
                # Skip large files
                if file_info['size'] > 512 * 1024:
                    print(" Skipped (too large)")
                    continue
                
                # Get structural analysis
                analyzer = CodeAnalyzer()
                structure_info = {}
                
                if file_info['language'] == 'python':
                    structure_info = analyzer.analyze_python_code(file_info['content'])
                    # Add to project dependencies
                    project_info['dependencies'].update(structure_info.get('dependencies', []))
                
                # Get Ollama analysis
                ollama_analysis = analyze_with_ollama(file_info, structure_info)
                
                # Generate documentation
                documentation = generate_documentation(file_info, structure_info, ollama_analysis)
                
                # Save to database
                if save_to_db(conn, file_info, structure_info, ollama_analysis, documentation):
                    print(" Done!")
                else:
                    print(" Failed to save")
                
                # Update language stats
                lang = file_info['language']
                project_info['languages'][lang] = project_info['languages'].get(lang, 0) + 1
                
            except Exception as e:
                print(f" Error: {e}")
    
    # Save project summaries
    for project_name, project_info in all_projects.items():
        project_info['dependencies'] = list(project_info['dependencies'])
        doc_path = Path(project_name) / 'PROJECT_DOCUMENTATION.json'
        with open(doc_path, 'w') as f:
            json.dump(project_info, f, indent=2)
        print(f"\nProject documentation saved to: {doc_path}")
    
    conn.close()
    print("\nAnalysis complete!")

if __name__ == '__main__':
    main()
