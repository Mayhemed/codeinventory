import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set

class EnhancedScanner:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        
    def analyze_python_file(self, file_path: Path) -> Dict:
        """Analyze Python file for imports and structure."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
            
            imports = []
            functions = []
            classes = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({
                            'module': alias.name,
                            'alias': alias.asname,
                            'line': node.lineno
                        })
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        imports.append({
                            'module': f"{module}.{alias.name}",
                            'alias': alias.asname,
                            'line': node.lineno,
                            'from_import': True
                        })
                elif isinstance(node, ast.FunctionDef):
                    functions.append({
                        'name': node.name,
                        'line': node.lineno,
                        'args': [arg.arg for arg in node.args.args],
                        'decorators': [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list]
                    })
                elif isinstance(node, ast.ClassDef):
                    classes.append({
                        'name': node.name,
                        'line': node.lineno,
                        'bases': [base.id if isinstance(base, ast.Name) else str(base) for base in node.bases],
                        'methods': []
                    })
            
            # Detect if this is an entry point
            is_entry_point = 'if __name__ == "__main__"' in content or 'if __name__ == \'__main__\'' in content
            
            # Determine project structure
            relative_path = file_path.relative_to(self.base_path)
            parts = relative_path.parts
            
            project = parts[0] if len(parts) > 1 else 'root'
            module = '.'.join(parts[1:-1]) if len(parts) > 2 else None
            
            return {
                'imports': imports,
                'functions': functions,
                'classes': classes,
                'is_entry_point': is_entry_point,
                'project': project,
                'module': module,
                'parent_path': str(file_path.parent.relative_to(self.base_path))
            }
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return {}
    
    def analyze_javascript_file(self, file_path: Path) -> Dict:
        """Analyze JavaScript file for imports and structure."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        imports = []
        
        # Find ES6 imports
        es6_imports = re.findall(r'import\s+(?:{[^}]+}|[\w\s,]+)\s+from\s+[\'"]([^\'"]+)[\'"]', content)
        for imp in es6_imports:
            imports.append({'module': imp, 'type': 'es6'})
        
        # Find CommonJS requires
        cjs_requires = re.findall(r'require\([\'"]([^\'"]+)[\'"]\)', content)
        for req in cjs_requires:
            imports.append({'module': req, 'type': 'commonjs'})
        
        # Detect if this is an entry point
        is_entry_point = bool(re.search(r'(app\.listen|server\.listen)', content))
        
        # Determine project structure
        relative_path = file_path.relative_to(self.base_path)
        parts = relative_path.parts
        
        project = parts[0] if len(parts) > 1 else 'root'
        module = '.'.join(parts[1:-1]) if len(parts) > 2 else None
        
        return {
            'imports': imports,
            'is_entry_point': is_entry_point,
            'project': project,
            'module': module,
            'parent_path': str(file_path.parent.relative_to(self.base_path))
        }
