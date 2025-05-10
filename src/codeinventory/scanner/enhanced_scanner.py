import ast
import re
from pathlib import Path
from typing import Dict, List, Optional

class EnhancedAnalyzer:
    def __init__(self):
        pass
    
    def analyze_file(self, file_path: str, content: str, language: str) -> Dict:
        """Analyze a file for execution and import information."""
        if language == 'python':
            return self.analyze_python(file_path, content)
        elif language in ['javascript', 'typescript']:
            return self.analyze_javascript(file_path, content)
        elif language in ['shell', 'bash']:
            return self.analyze_shell(file_path, content)
        return {}
    
    def analyze_python(self, file_path: str, content: str) -> Dict:
        """Analyze Python file for execution and import patterns."""
        result = {
            'execution_command': None,
            'importable_items': [],
            'requires_args': False,
            'environment_vars': [],
            'dependencies': []
        }
        
        try:
            tree = ast.parse(content)
            
            # Check if it's executable
            has_main = False
            has_argparse = False
            has_click = False
            functions = []
            classes = []
            
            for node in ast.walk(tree):
                # Check for if __name__ == "__main__":
                if isinstance(node, ast.If):
                    if isinstance(node.test, ast.Compare):
                        if isinstance(node.test.left, ast.Name) and node.test.left.id == '__name__':
                            has_main = True
                
                # Check for imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == 'argparse':
                            has_argparse = True
                        elif alias.name == 'click':
                            has_click = True
                        result['dependencies'].append(alias.name)
                
                if isinstance(node, ast.ImportFrom):
                    if node.module == 'click':
                        has_click = True
                    elif node.module:
                        result['dependencies'].append(node.module)
                
                # Collect functions and classes
                if isinstance(node, ast.FunctionDef):
                    # Skip private functions
                    if not node.name.startswith('_'):
                        doc = ast.get_docstring(node) or ""
                        functions.append({
                            'name': node.name,
                            'args': [arg.arg for arg in node.args.args],
                            'doc': doc.split('\n')[0] if doc else None
                        })
                
                if isinstance(node, ast.ClassDef):
                    if not node.name.startswith('_'):
                        doc = ast.get_docstring(node) or ""
                        classes.append({
                            'name': node.name,
                            'doc': doc.split('\n')[0] if doc else None
                        })
            
            # Determine execution command
            file_name = Path(file_path).name
            if has_main:
                if has_click:
                    result['execution_command'] = f"python {file_name} --help"
                    result['requires_args'] = True
                elif has_argparse:
                    result['execution_command'] = f"python {file_name} -h"
                    result['requires_args'] = True
                else:
                    result['execution_command'] = f"python {file_name}"
            
            # Set importable items
            result['importable_items'] = {
                'functions': functions,
                'classes': classes
            }
            
            # Look for environment variables
            env_pattern = r'os\.environ\.get\([\'"](\w+)[\'"]'
            env_vars = re.findall(env_pattern, content)
            result['environment_vars'] = list(set(env_vars))
            
        except Exception as e:
            print(f"Error analyzing Python file: {e}")
        
        return result
    
    def analyze_javascript(self, file_path: str, content: str) -> Dict:
        """Analyze JavaScript file for execution patterns."""
        result = {
            'execution_command': None,
            'importable_items': [],
            'requires_args': False,
            'environment_vars': [],
            'dependencies': []
        }
        
        file_name = Path(file_path).name
        
        # Check if it's a Node.js script
        if 'require(' in content or 'import ' in content:
            # Check for common patterns
            if 'express' in content or 'app.listen' in content:
                result['execution_command'] = f"node {file_name}"
            elif 'process.argv' in content:
                result['execution_command'] = f"node {file_name} [args]"
                result['requires_args'] = True
            else:
                result['execution_command'] = f"node {file_name}"
        
        # Find exports
        exports = []
        
        # CommonJS exports
        export_patterns = [
            r'module\.exports\s*=\s*{([^}]+)}',
            r'exports\.(\w+)\s*=',
            r'module\.exports\.(\w+)\s*='
        ]
        
        for pattern in export_patterns:
            matches = re.findall(pattern, content)
            exports.extend(matches)
        
        # ES6 exports
        es6_patterns = [
            r'export\s+function\s+(\w+)',
            r'export\s+class\s+(\w+)',
            r'export\s+const\s+(\w+)',
            r'export\s+{\s*([^}]+)\s*}'
        ]
        
        for pattern in es6_patterns:
            matches = re.findall(pattern, content)
            exports.extend(matches)
        
        result['importable_items'] = list(set(exports))
        
        # Find environment variables
        env_patterns = [
            r'process\.env\.(\w+)',
            r'process\.env\[[\'"](\w+)[\'"]\]'
        ]
        
        env_vars = []
        for pattern in env_patterns:
            matches = re.findall(pattern, content)
            env_vars.extend(matches)
        
        result['environment_vars'] = list(set(env_vars))
        
        return result
    
    def analyze_shell(self, file_path: str, content: str) -> Dict:
        """Analyze shell script for execution patterns."""
        result = {
            'execution_command': None,
            'importable_items': [],
            'requires_args': False,
            'environment_vars': [],
            'dependencies': []
        }
        
        file_name = Path(file_path).name
        
        # Check shebang
        if content.startswith('#!'):
            result['execution_command'] = f"./{file_name}"
        else:
            result['execution_command'] = f"bash {file_name}"
        
        # Check for arguments
        if '$1' in content or '$@' in content or '$*' in content:
            result['requires_args'] = True
            result['execution_command'] += " [args]"
        
        # Find environment variables
        env_pattern = r'\$(\w+)'
        env_vars = re.findall(env_pattern, content)
        # Filter out common shell variables
        shell_vars = {'1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '@', '*', '#', '?', '-', '$', '!'}
        result['environment_vars'] = [var for var in set(env_vars) if var not in shell_vars]
        
        return result
