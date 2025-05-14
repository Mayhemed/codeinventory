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
import sys
from typing import Dict, List, Optional, Tuple
import concurrent.futures
import threading
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description='Comprehensive Code Scanner')
    parser.add_argument('path', nargs='?', default='.', help='Path to scan (default: current directory)')
    parser.add_argument('--custom', '-c', action='store_true', help='Focus on custom code only')
    parser.add_argument('--skip-analysis', '-s', action='store_true', help='Skip AI analysis')
    parser.add_argument('--max-size', '-m', type=int, default=1000000, help='Maximum file size in bytes')
    parser.add_argument('--workers', '-w', type=int, default=5, help='Number of worker threads (default: 5)')
    parser.add_argument('--quiet', '-q', action='store_true', help='Reduce output verbosity')
    parser.add_argument('--no-docs', '-d', action='store_true', help='Skip generating documentation files')
    return parser.parse_args()

# Configuration
OLLAMA_HOST = "http://localhost:11434"
MODEL = "codellama"
DB_PATH = os.path.expanduser("~/.codeinventory/inventory.db")
TIMEOUT = 120  # Increased timeout for Ollama requests
MAX_OLLAMA_WORKERS = 5

def process_single_file(file_path: Path, scan_path_base: Path, skip_analysis: bool = False, skip_docs: bool = False) -> str:
    """Processes a single file, including creating its own DB connection and CodeAnalyzer instance."""
    thread_conn = None
    analyzer_instance = CodeAnalyzer() # Instantiate CodeAnalyzer per task for thread safety

    # Default relative_path, will be updated if possible
    relative_path_str = file_path.name # Fallback to just the filename

    try:
        thread_conn = sqlite3.connect(DB_PATH, timeout=10) # Each thread gets its own connection

        try:
            # Ensure both paths are absolute for reliable relative_to comparison
            abs_file_path = file_path.resolve()
            abs_scan_path_base = scan_path_base.resolve()
            if abs_file_path.is_relative_to(abs_scan_path_base):
                relative_path_str = str(abs_file_path.relative_to(abs_scan_path_base))
            # else: use file_path.name (already set)
        except ValueError:
            # This can happen if file_path is not under scan_path_base (e.g., symlink outside tree)
            relative_path_str = file_path.name # Fallback
        except Exception as e_rel:
            # print(f"  Warning: Could not determine relative path for {file_path}: {e_rel}")
            relative_path_str = file_path.name # Fallback

        file_info = get_file_info(file_path)

        if file_info['size'] > 1 * 1024 * 1024:
            return "skipped_large"
        if not file_info['content'].strip():
            return "skipped_empty"

        structure_info = {}
        if file_info['language'] == 'python':
            structure_info = analyzer_instance.analyze_python_code(str(file_path), file_info['content'])
        elif file_info['language'] in ['shell', 'bash', 'zsh']:
            structure_info = analyzer_instance.analyze_other_code(str(file_path), file_info['content'], file_info['language'])
        else:
            structure_info = analyzer_instance.analyze_other_code(str(file_path), file_info['content'], file_info['language'])

        ai_analysis = None
        if not skip_analysis:
            ai_analysis = analyze_with_ollama(file_info, structure_info)

        analysis_to_use = ai_analysis if ai_analysis and isinstance(ai_analysis, dict) and len(ai_analysis) > 1 else generate_enhanced_analysis(file_info, structure_info)

        documentation = generate_documentation(file_info, structure_info, analysis_to_use)

        if save_to_db(thread_conn, file_info, structure_info, analysis_to_use, documentation):
            # Generate documentation files if not skipped
            if not skip_docs:
                doc_dir = file_path.parent / '__code_docs__'
                doc_dir.mkdir(exist_ok=True)
                doc_file_json = doc_dir / f"{file_path.stem}_analysis.json"
                doc_file_md = doc_dir / f"{file_path.stem}_analysis.md"
                try:
                    with open(doc_file_json, 'w', encoding='utf-8') as f_json:
                        json.dump(documentation, f_json, indent=2)
                    create_markdown_doc(documentation, doc_file_md)
                except Exception as e_write:
                    # print(f"  Error writing doc files for {relative_path_str}: {e_write}")
                    pass
            return "success"
        else:
            return "db_error"

    except Exception as e:
        # print(f"  Processing Error for {relative_path_str}: {type(e).__name__} - {e}")
        import traceback
        # print(f"Traceback for {relative_path_str} error:")
        # traceback.print_exc() # Uncomment for detailed traceback per file error
        return f"processing_error ({type(e).__name__})"
    finally:
        if thread_conn:
            thread_conn.close()
            
class CodeAnalyzer:
    def __init__(self):
        self.reset()

    def reset(self):
        self.imports, self.functions, self.classes, self.global_vars = [], [], [], []
        self.dependencies, self.constants, self.decorators, self.docstrings = set(), [], [], []
        self.execution_command, self.requires_args, self.environment_vars = None, False, []

    def _get_decorator_name(self, decorator):
        if isinstance(decorator, ast.Name): return decorator.id
        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name): return decorator.func.id
        if isinstance(decorator, ast.Attribute) and isinstance(decorator.value, ast.Name): return f"{decorator.value.id}.{decorator.attr}"
        return None

    def _extract_function_info(self, node, is_method=False):
        func_info = {'name':node.name,'args':[],'returns':None,'decorators':[],'docstring':ast.get_docstring(node),
                     'is_async':isinstance(node,ast.AsyncFunctionDef),'line':node.lineno,'complexity':self._calculate_complexity(node)}
        if is_method: func_info['is_method'] = True
        for dec_node in node.decorator_list:
            dec_name = self._get_decorator_name(dec_node)
            if dec_name: func_info['decorators'].append(dec_name); self.decorators.append({'name':dec_name,'target':node.name,'type':'method' if is_method else 'function'})
        
        arg_list = []
        current_args = node.args.args
        current_defaults = node.args.defaults

        all_arg_nodes = current_args
        if hasattr(node.args, 'posonlyargs'):
            all_arg_nodes = node.args.posonlyargs + current_args
        if hasattr(node.args, 'kwonlyargs'):
            all_arg_nodes.extend(node.args.kwonlyargs)


        for arg_node in all_arg_nodes:
            arg_info = {'name':arg_node.arg,'type':None,'default':None}
            if arg_node.annotation: 
                try: arg_info['type']=ast.unparse(arg_node.annotation) 
                except AttributeError: arg_info['type']=ast.dump(arg_node.annotation) 
            arg_list.append(arg_info)

        num_reg_arg_defaults = len(current_defaults)
        for i, def_node in enumerate(current_defaults):
            arg_idx_in_all_arg_nodes = (len(node.args.posonlyargs) if hasattr(node.args, 'posonlyargs') else 0) + \
                                   len(node.args.args) - num_reg_arg_defaults + i
            if arg_idx_in_all_arg_nodes < len(arg_list):
                 try: arg_list[arg_idx_in_all_arg_nodes]['default']=ast.unparse(def_node) 
                 except AttributeError: arg_list[arg_idx_in_all_arg_nodes]['default']=ast.dump(def_node)
        
        if hasattr(node.args, 'kw_defaults'):
            for i, def_node in enumerate(node.args.kw_defaults):
                if def_node is not None: 
                    kwonlyarg_node = node.args.kwonlyargs[i]
                    for arg_info_item in arg_list:
                        if arg_info_item['name'] == kwonlyarg_node.arg:
                            try: arg_info_item['default'] = ast.unparse(def_node)
                            except AttributeError: arg_info_item['default'] = ast.dump(def_node)
                            break
        
        func_info['args'] = arg_list

        if node.returns: 
            try: func_info['returns']=ast.unparse(node.returns) 
            except AttributeError: func_info['returns']=ast.dump(node.returns)
        return func_info

    def _extract_class_info(self, node):
        class_info = {'name':node.name,'bases':[],'methods':[],'attributes':[],'decorators':[],'docstring':ast.get_docstring(node),
                      'line':node.lineno,'is_dataclass':False,'metaclass':None}
        for dec_node in node.decorator_list:
            dec_name = self._get_decorator_name(dec_node)
            if dec_name: class_info['decorators'].append(dec_name); self.decorators.append({'name':dec_name,'target':node.name,'type':'class'})
            if dec_name=='dataclass': class_info['is_dataclass']=True
        for base_node in node.bases: 
            try: class_info['bases'].append(ast.unparse(base_node)) 
            except AttributeError: class_info['bases'].append(ast.dump(base_node))
        for item in node.body:
            if isinstance(item,(ast.FunctionDef,ast.AsyncFunctionDef)): class_info['methods'].append(self._extract_function_info(item,is_method=True))
            elif isinstance(item,ast.Assign):
                for target in item.targets:
                    if isinstance(target,ast.Name): class_info['attributes'].append({'name':target.id,'line':item.lineno,'has_type_hint':False})
            elif isinstance(item,ast.AnnAssign) and isinstance(item.target,ast.Name):
                attr_info={'name':item.target.id,'line':item.lineno,'has_type_hint':True,'type':None}
                if item.annotation: 
                    try: attr_info['type']=ast.unparse(item.annotation) 
                    except AttributeError: attr_info['type']=ast.dump(item.annotation)
                class_info['attributes'].append(attr_info)
        return class_info

    def _calculate_complexity(self, node):
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child,(ast.If,ast.While,ast.For,ast.AsyncFor,ast.ExceptHandler,ast.With,ast.AsyncWith)): complexity+=1
            elif isinstance(child,ast.BoolOp) and hasattr(child, 'op') and isinstance(child.op, (ast.And, ast.Or)): complexity+=len(child.values)-1
        return complexity
        
    def analyze_python_code(self, file_path_str: str, code: str):
        self.reset()
        file_name = Path(file_path_str).name
        try:
            tree = ast.parse(code)
            mod_doc = ast.get_docstring(tree)
            if mod_doc: self.docstrings.append({'type':'module','content':mod_doc})
            has_main,has_argparse,has_click = False,False,False
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):
                    for alias in node.names:
                        self.imports.append({'type':'import','module':alias.name,'alias':alias.asname,'line':node.lineno})
                        self.dependencies.add(alias.name.split('.')[0])
                        if alias.name=='argparse':has_argparse=True
                        if alias.name=='click':has_click=True
                elif isinstance(node,ast.ImportFrom):
                    mod=node.module or '';
                    for alias in node.names:
                        self.imports.append({'type':'from','module':mod,'name':alias.name,'alias':alias.asname,'line':node.lineno})
                        if mod:self.dependencies.add(mod.split('.')[0])
                        if mod=='click':has_click=True
                elif isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):self.functions.append(self._extract_function_info(node))
                elif isinstance(node,ast.ClassDef):self.classes.append(self._extract_class_info(node))
                elif isinstance(node,ast.Assign) and getattr(node,'col_offset',-1)==0: 
                    for target in node.targets:
                        if isinstance(target,ast.Name):(self.constants if target.id.isupper() else self.global_vars).append({'name':target.id,'line':node.lineno})
                
                if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
                    if isinstance(node.test.left, ast.Name) and node.test.left.id == '__name__':
                        if len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Eq):
                            if (isinstance(node.test.comparators[0], ast.Constant) and node.test.comparators[0].value == '__main__') or \
                               (isinstance(node.test.comparators[0], ast.Str) and node.test.comparators[0].s == '__main__'): 
                                has_main = True
            if has_main:
                if has_click:self.execution_command,self.requires_args=f"python {file_name} --help",True
                elif has_argparse:self.execution_command,self.requires_args=f"python {file_name} -h",True
                else:self.execution_command=f"python {file_name}"
            
            env_vars_found = re.findall(r'os\.environ\.get\([\'"]([\w_]+)[\'"]|\bos\.getenv\([\'"]([\w_]+)[\'"]', code)
            self.environment_vars = list(set(v1 or v2 for v1,v2 in env_vars_found if v1 or v2))

        except SyntaxError as e: print(f"  AST SyntaxError in {file_name}:{getattr(e, 'lineno', '?')}: {getattr(e, 'msg', e)}")
        except Exception as e: print(f"  AST Error in {file_name}: {type(e).__name__} - {e}")
        
        return {'imports':self.imports,'functions':self.functions,'classes':self.classes,'global_vars':self.global_vars,
                'constants':self.constants,'dependencies':list(self.dependencies),'decorators':self.decorators,
                'docstrings':self.docstrings,'execution_command':self.execution_command,
                'requires_args':self.requires_args,'environment_vars':self.environment_vars}
    
    def analyze_other_code(self, file_path_str: str, content: str, language: str):
        self.reset()
        file_name = Path(file_path_str).name
        if language in ['shell', 'bash', 'zsh']:
            self.execution_command = f"./{file_name}" if content.startswith('#!') else f"{language} {file_name}"
            # Detect if script uses positional parameters ($1, $*, $@, $#) or reads input
            if re.search(r'\$[0-9@#*?]|\bread\b', content):
                self.requires_args = True
                # Append to existing command, don't overwrite if already set (e.g. by shebang)
                self.execution_command = (self.execution_command or f"./{file_name}") + " [args...]"

            # Find environment variables like $VAR or ${VAR}
            # Exclude special shell variables that are not typically "environment" vars set by user
            env_vars_found = re.findall(r'\$(?:\{([\w_]+)\}|([\w_]+))', content)
            special_shell_vars = {'_', '?', '#', '*', '@', '!', '$'} # Add more if needed
            self.environment_vars = list(set(
                var_name for group in env_vars_found
                for var_name in group if var_name and not var_name.isdigit() and var_name not in special_shell_vars
            ))
        # For other languages, you might add basic analysis here if needed
        return {'imports':[],'functions':[],'classes':[],'global_vars':[],'constants':[],'dependencies':[],
                'decorators':[],'docstrings':[],'execution_command':self.execution_command,
                'requires_args':self.requires_args,'environment_vars':self.environment_vars}

def get_file_info(filepath: Path) -> Dict:
    stats = filepath.stat()
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        # print(f"  Error reading file {filepath}: {e}")
        content = "" 
    
    lines = content.split('\n')
    code_lines_count = 0
    comment_lines_count = 0
    lang = get_language(filepath) # Get language once
    for line in lines:
        stripped_line = line.strip()
        if not stripped_line: # Skip empty lines
            continue
        
        is_comment = False
        if lang == 'python' and stripped_line.startswith('#'):
            is_comment = True
        elif lang in ['javascript', 'typescript', 'c', 'cpp', 'java', 'go', 'rust', 'csharp', 'swift', 'kotlin'] and stripped_line.startswith('//'):
            is_comment = True
        elif lang in ['shell', 'bash', 'zsh', 'ruby', 'perl'] and stripped_line.startswith('#'): # Common for more scripting langs
             is_comment = True
        # Add more language comment styles if needed (e.g., /* ... */ for block, -- for SQL)

        if is_comment:
            comment_lines_count += 1
        else: # Not empty and not a full line comment (or not recognized as such)
            code_lines_count +=1
            
    return {
        'path': str(filepath), 'name': filepath.name, 'type': 'module', # type could be enhanced
        'language': lang, 'content': content,
        'hash': hashlib.md5(content.encode('utf-8', 'ignore')).hexdigest(),
        'size': stats.st_size, 'last_modified': int(stats.st_mtime * 1000),
        'total_lines': len(lines), 'code_lines': code_lines_count, 'comment_lines': comment_lines_count
    }

def get_language(filepath: Path) -> str:
    name_lower=filepath.name.lower()
    if name_lower=='dockerfile':return 'dockerfile'
    if name_lower=='makefile':return 'makefile'
    # Add other common non-extension specific names if any: e.g., Jenkinsfile -> groovy
    
    ext=filepath.suffix.lower()
    mapping={'.py':'python','.pyw':'python','.js':'javascript','.jsx':'javascript','.mjs':'javascript',
               '.ts':'typescript','.tsx':'typescript','.sh':'shell','.bash':'bash','.zsh':'zsh', # Specific shell types
               '.html':'html','.htm':'html','.css':'css','.scss':'scss','.sass':'sass','.json':'json',
               '.yaml':'yaml','.yml':'yaml','.md':'markdown','.sql':'sql','.r':'r','.java':'java',
               '.c':'c','.cpp':'cpp','.h':'c','.hpp':'cpp','.cs':'csharp','.go':'go','.php':'php',
               '.rb':'ruby','.swift':'swift','.kt':'kotlin','.rs':'rust','.pl':'perl','.lua':'lua',
               '.xml':'xml', '.ini':'ini', '.toml':'toml', '.cfg':'cfg', '.tf':'terraform', '.hcl': 'terraform',
               '.gradle': 'groovy', '.Jenkinsfile': 'groovy' # Example, Jenkinsfile might not have suffix
               }
    return mapping.get(ext,'text')


def analyze_with_ollama(file_info: Dict, structure_info: Dict) -> Optional[Dict]:
    functions = structure_info.get('functions', [])
    classes = structure_info.get('classes', [])
    imports = structure_info.get('imports', [])
    
    function_names = [f['name'] for f in functions[:5]]
    class_names = [c['name'] for c in classes[:5]]
    import_names = [imp.get('module', imp.get('name', 'unknown_import')) for imp in imports[:5]]

    exec_info_prompt = ""
    if structure_info.get('execution_command'):
        exec_info_prompt = f"\nExecution Hint: Likely runs with `{structure_info['execution_command']}`. Requires args: {structure_info.get('requires_args', False)}."

    prompt = f"""You are analyzing a {file_info['language']} code file. Please provide a comprehensive analysis.

File: {file_info['name']}
Path: {file_info['path']} 
Language: {file_info['language']}
Size: {file_info['size']} bytes
Lines: {file_info.get('total_lines', 0)} total, {file_info.get('code_lines', 0)} code
{exec_info_prompt}

Structure Summary:
- Imports: {len(imports)} ({', '.join(import_names)}{'...' if len(import_names) < len(imports) else ''})
- Functions: {len(functions)} ({', '.join(function_names)}{'...' if len(function_names) < len(functions) else ''})
- Classes: {len(classes)} ({', '.join(class_names)}{'...' if len(class_names) < len(classes) else ''})

Code sample (first ~1500 chars):
{file_info['content'][:1500]}

Analyze this code and provide a JSON response with the following fields:
{{
  "purpose": "A clear, specific, one-sentence description of what this code primarily does and its main goal.",
  "description": "A detailed explanation (2-4 sentences) of the code's functionality, key operations, and how it achieves its purpose. Mention any notable architectural patterns or design choices if apparent.",
  "category": "Choose the MOST appropriate single category: api, ui, data-processing, data-visualization, machine-learning, automation-script, utility-library, build-tool, test-script, configuration, documentation, example-code, database-related, security, networking, os-interaction, scientific-computing, game-dev, other",
  "complexity": "Choose one: simple, moderate, complex. Justify briefly based on code length, number of components, dependencies, and logic intricacy.",
  "main_functionality": ["List up to 5 main features or capabilities as concise strings."],
  "dependencies_analysis": "Briefly state key external libraries/modules used and their role (e.g., 'Uses pandas for data manipulation, matplotlib for plotting').",
  "potential_issues": ["List up to 3 potential problems or areas for improvement (e.g., error handling, performance bottlenecks, outdated practices). If none apparent, use an empty list or state 'None identified.'."],
  "usage_examples": ["Provide one or two brief, conceptual examples of how this code might be used or invoked if it's a script/library. For scripts, suggest a hypothetical command line usage. Use an empty list if not applicable."]
}}

Provide ONLY the valid JSON response. Do not include any other text, greetings, or explanations outside the JSON structure.
The entire response must be a single JSON object.
"""
    raw_response_content = None # Initialize for use in error messages
    try:
        # Add a timeout parameter to avoid hanging
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": MODEL, "prompt": prompt, "temperature": 0.2, "stream": False, "format": "json"},
            timeout=TIMEOUT
        )
        
        # Handle HTTP errors explicitly
        if response.status_code != 200:
            print(f"  (Ollama HTTP error for {file_info['name']}: {response.status_code})")
            return None
            
        result = response.json()
        raw_response_content = result.get('response', '')
        
        if not raw_response_content.strip():
            print(f"  (Ollama returned empty response for {file_info['name']})")
            return None

        try:
            ai_json_response = json.loads(raw_response_content)
            if isinstance(ai_json_response, dict) and "purpose" in ai_json_response:
                return ai_json_response
            else:
                print(f"  (Ollama JSON for {file_info['name']} not valid dict or misses 'purpose')")
                return extract_fields_fallback(raw_response_content, file_info['name'])
        except json.JSONDecodeError as e:
            print(f"  (Ollama JSON parse error for {file_info['name']}: {e}. Attempting fallback.)")
            return extract_fields_fallback(raw_response_content, file_info['name'])
    
    except requests.Timeout:
        print(f"  (Ollama request timeout for {file_info['name']} after {TIMEOUT}s)")
        return None
    except requests.RequestException as e:
        print(f"  (Ollama request error for {file_info['name']}: {type(e).__name__} - {str(e)[:100]})")
        return None
    except Exception as e:
        print(f"  (Unexpected error during Ollama analysis for {file_info['name']}: {type(e).__name__} - {str(e)[:100]})")
        return None


def extract_fields_fallback(text: str, filename_for_log:str = "unknown_file") -> Optional[Dict]:
    if not text or not text.strip():
        return None
    data = {}
    try:
        # Try to find the largest JSON blob first
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                potential_json = json.loads(match.group(0))
                if isinstance(potential_json, dict): # If it's a dict, assume it's the best we can get
                    return potential_json # Return it even if not perfect, generate_enhanced_analysis is the ultimate fallback
            except json.JSONDecodeError:
                pass # Continue to field-by-field extraction if blob parsing fails

        # Fallback to individual field extraction (less reliable)
        # Using DOTALL to match newlines in descriptions, etc.
        patterns = {
            "purpose": r'"purpose":\s*"([^"]*)"',
            "description": r'"description":\s*"((?:[^"\\]|\\.)*)"', # Handles escaped quotes in description
            "category": r'"category":\s*"([^"]*)"',
            "complexity": r'"complexity":\s*"([^"]*)"',
            # Array fields are harder with simple regex, but can try for simple cases
            "main_functionality": r'"main_functionality":\s*\[([^\]]*)\]',
            "potential_issues": r'"potential_issues":\s*\[([^\]]*)\]',
            "usage_examples": r'"usage_examples":\s*\[([^\]]*)\]'
        }
        for key, pattern in patterns.items():
            m = re.search(pattern, text, re.DOTALL)
            if m:
                if key in ["main_functionality", "potential_issues", "usage_examples"]:
                    # For arrays, split the content by comma, strip quotes and spaces
                    # This is a simplification and might not handle all JSON array complexities
                    array_content = m.group(1).strip()
                    if array_content: # If not empty array string
                        data[key] = [s.strip().strip('"').strip("'") for s in array_content.split(',') if s.strip()]
                    else:
                        data[key] = []
                else:
                    data[key] = m.group(1).strip()
        
        # If we extracted anything, return it. Otherwise, None.
        return data if data and "purpose" in data else None # Require at least 'purpose'
    except Exception as e:
        # print(f"  (Error in extract_fields_fallback for {filename_for_log}: {e})")
        return None


def generate_enhanced_analysis(file_info: Dict, structure_info: Dict) -> Dict:
    lang = file_info.get('language', 'unknown language')
    name = file_info.get('name', 'unknown file')
    deps_count = len(structure_info.get('dependencies', []))
    deps_analysis_str = f"Uses {deps_count} unique dependencies." if deps_count > 0 else "No explicit dependencies identified by static analysis."

    return {
        'purpose': f"A {lang} file named {name}.",
        'description': "Basic structural analysis performed. AI analysis was not available, failed, or was skipped. Review manually for detailed insights.",
        'category': 'utility', # Default, consider 'other' or more dynamic based on lang
        'complexity': 'unknown', # Cannot determine without deeper analysis or AI
        'main_functionality': [],
        'dependencies_analysis': deps_analysis_str,
        'potential_issues': ["AI analysis not available; detailed review recommended."],
        'usage_examples': []
    }


def generate_documentation(file_info: Dict, structure_info: Dict, analysis: Dict) -> Dict:
    analysis = analysis if isinstance(analysis, dict) else {}
    
    execution_info_data = {
        'command': structure_info.get('execution_command'),
        'requires_args': structure_info.get('requires_args', False),
        'environment_vars': structure_info.get('environment_vars', [])
    }

    # Ensure all expected keys from AI analysis have a default if missing
    doc_summary_fields = [
        'summary', 'description', 'category', 'complexity', 
        'architectural_role', 'main_functionality', 'patterns', 
        'dependencies_analysis', 'potential_issues', 'security_considerations',
        'performance_notes', 'maintainability', 'test_coverage', 'usage_examples'
    ]
    curated_documentation_summary = {}
    for field in doc_summary_fields:
        default_value = [] if field.endswith('_issues') or field.endswith('_examples') or field.endswith('_functionality') or field.endswith('_vars') or field == 'patterns' else ''
        if field == 'summary': # Special case: map 'purpose' from AI to 'summary' in docs
            curated_documentation_summary[field] = analysis.get('purpose', default_value)
        else:
            curated_documentation_summary[field] = analysis.get(field, default_value)


    doc = {
        'file': file_info['name'],
        'path': file_info['path'],
        'language': file_info['language'],
        'last_analyzed': datetime.now().isoformat(),
        'metrics': {
            'size': file_info['size'],
            'lines': {'total': file_info.get('total_lines',0), 'code': file_info.get('code_lines',0), 'comment': file_info.get('comment_lines',0)},
            'complexity': {'overall': analysis.get('complexity', 'unknown'), 'functions': len(structure_info.get('functions',[])), 'classes': len(structure_info.get('classes',[])), 'imports': len(structure_info.get('imports',[]))}
        },
        'structure': {**structure_info, 'execution_info': execution_info_data},
        'analysis': analysis, 
        'documentation': curated_documentation_summary, # Use the curated summary
        'dependency_graph': {
            'imports': structure_info.get('imports', []),
            'dependencies': structure_info.get('dependencies', []),
            'exported': {
                'functions': [f['name'] for f in structure_info.get('functions', [])],
                'classes': [c['name'] for c in structure_info.get('classes', [])],
                'variables': [v['name'] for v in structure_info.get('global_vars', [])],
                'constants': [c['name'] for c in structure_info.get('constants', [])]
            }
        }
    }
    return doc

def init_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # cursor.execute("DROP TABLE IF EXISTS tools")
    # cursor.execute("DROP TABLE IF EXISTS dependencies")
    # cursor.execute("DROP TABLE IF EXISTS functions")
    # cursor.execute("DROP TABLE IF EXISTS classes")
    
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
            architectural_role TEXT,
            maintainability TEXT,
            last_modified INTEGER,
            last_analyzed INTEGER,
            created_at INTEGER DEFAULT (strftime('%s', 'now')),
            documentation TEXT,
            size INTEGER,
            total_lines INTEGER,
            code_lines INTEGER,
            comment_lines INTEGER,
            execution_command TEXT,
            requires_args BOOLEAN,
            environment_vars TEXT
        );
        
        CREATE TABLE IF NOT EXISTS dependencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_id TEXT NOT NULL,
            dependency TEXT NOT NULL,
            import_type TEXT,
            line_number INTEGER,
            FOREIGN KEY (tool_id) REFERENCES tools(id) ON DELETE CASCADE
        );
        
        CREATE TABLE IF NOT EXISTS functions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_id TEXT NOT NULL,
            name TEXT NOT NULL,
            args TEXT,
            returns TEXT,
            docstring TEXT,
            decorators TEXT,
            is_async BOOLEAN,
            complexity INTEGER,
            line_number INTEGER,
            FOREIGN KEY (tool_id) REFERENCES tools(id) ON DELETE CASCADE
        );
        
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_id TEXT NOT NULL,
            name TEXT NOT NULL,
            bases TEXT,
            methods TEXT,
            attributes TEXT,
            docstring TEXT,
            decorators TEXT,
            is_dataclass BOOLEAN,
            line_number INTEGER,
            FOREIGN KEY (tool_id) REFERENCES tools(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_tools_path ON tools(path);
        CREATE INDEX IF NOT EXISTS idx_tools_name ON tools(name);
        CREATE INDEX IF NOT EXISTS idx_tools_language ON tools(language);
        CREATE INDEX IF NOT EXISTS idx_tools_category ON tools(category);
        CREATE INDEX IF NOT EXISTS idx_dependencies_tool_id ON dependencies(tool_id);
        CREATE INDEX IF NOT EXISTS idx_dependencies_dependency ON dependencies(dependency);
        CREATE INDEX IF NOT EXISTS idx_functions_tool_id ON functions(tool_id);
        CREATE INDEX IF NOT EXISTS idx_classes_tool_id ON classes(tool_id);
    """)
    
    conn.commit()
    # print("Database schema ensured by comprehensive_scanner.") # Less verbose
    return conn


def save_to_db(conn, file_info: Dict, structure_info: Dict, analysis: Dict, documentation: Dict):
    cursor = conn.cursor()
    timestamp = int(datetime.now().timestamp() * 1000)
    tool_id = file_info['hash']
    
    analysis = analysis if isinstance(analysis, dict) else {}
    doc_summary = documentation.get('documentation', {})

    try:
        cursor.execute("""
            INSERT OR REPLACE INTO tools (
                id, path, name, type, language, file_hash,
                purpose, description, category, complexity,
                architectural_role, maintainability,
                last_modified, last_analyzed, documentation,
                size, total_lines, code_lines, comment_lines,
                execution_command, requires_args, environment_vars
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tool_id, file_info['path'], file_info['name'], file_info['type'], file_info['language'], file_info['hash'],
            doc_summary.get('summary', analysis.get('purpose')), 
            doc_summary.get('description', analysis.get('description')),
            doc_summary.get('category', analysis.get('category')),
            doc_summary.get('complexity', analysis.get('complexity')),
            doc_summary.get('architectural_role', analysis.get('architectural_role')),
            doc_summary.get('maintainability', analysis.get('maintainability')),
            file_info['last_modified'], timestamp, json.dumps(documentation),
            file_info['size'], file_info.get('total_lines', 0), file_info.get('code_lines', 0), file_info.get('comment_lines', 0),
            structure_info.get('execution_command'), 
            structure_info.get('requires_args', False),
            json.dumps(structure_info.get('environment_vars', [])) 
        ))
        
        cursor.execute("DELETE FROM dependencies WHERE tool_id = ?", (tool_id,))
        for imp in structure_info.get('imports', []):
            cursor.execute("INSERT INTO dependencies (tool_id, dependency, import_type, line_number) VALUES (?, ?, ?, ?)",
                           (tool_id, imp.get('module', imp.get('name')), imp.get('type'), imp.get('line')))
        
        cursor.execute("DELETE FROM functions WHERE tool_id = ?", (tool_id,))
        for func in structure_info.get('functions', []):
            cursor.execute("INSERT INTO functions (tool_id, name, args, returns, docstring, decorators, is_async, complexity, line_number) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (tool_id, func.get('name'), json.dumps(func.get('args')), func.get('returns'), func.get('docstring'), json.dumps(func.get('decorators')), func.get('is_async'), func.get('complexity'), func.get('line')))
        
        cursor.execute("DELETE FROM classes WHERE tool_id = ?", (tool_id,))
        for cls in structure_info.get('classes', []):
            cursor.execute("INSERT INTO classes (tool_id, name, bases, methods, attributes, docstring, decorators, is_dataclass, line_number) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (tool_id, cls.get('name'), json.dumps(cls.get('bases')), json.dumps(cls.get('methods')), json.dumps(cls.get('attributes')), cls.get('docstring'), json.dumps(cls.get('decorators')), cls.get('is_dataclass'), cls.get('line')))

        conn.commit()
        return True
    except Exception as e:
        # print(f"  DB error during save_to_db for {file_info['name']}: {e}")
        # import traceback
        # traceback.print_exc()
        conn.rollback()
        return False

def scan_directory(directory: Path, exclude_patterns: List[str] = None) -> List[Path]:
    if exclude_patterns is None:
        exclude_patterns = [
            '__pycache__', '.git', 'node_modules', 'venv', '.venv',
            'env', '.env', 'site-packages', 'dist', 'build', '.pytest_cache', '.tox',
            'egg-info', 'wheels', 'lib/python', 'vendor', 'cache', '.idea', '.vscode',
            'migrations', 'deps',
            '*.pyc', '*.pyo', '*.egg-info', '.DS_Store', '.*'
        ]
    
    files = []
    try:
        for root, dirs, filenames in os.walk(directory):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns) and not d.startswith('.')]
            
            for filename in filenames:
                file_path = Path(os.path.join(root, filename))
                
                # Skip files larger than max size - adjust as needed if you don't have a config
                try:
                    # Adjust this line to match your actual config structure
                    if file_path.stat().st_size > 1_000_000:  # 1MB default
                        continue
                except Exception:
                    continue
                
                # Check if file extension is supported
                supported_suffixes = ['.py', '.js', '.jsx', '.ts', '.tsx', '.sh', '.bash', '.zsh',
                                      '.html', '.css', '.json', '.yaml', '.yml', '.md',
                                      '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.go',
                                      '.php', '.rb', '.swift', '.kt', '.rs', '.pl', '.lua',
                                      '.r', '.sql', '.txt', '.ini', '.toml', '.cfg', '.xml', 
                                      '.tf', '.hcl', '.gradle']
                
                if file_path.name.lower() in ['dockerfile', 'makefile', 'jenkinsfile'] or file_path.suffix.lower() in supported_suffixes:
                    # Final check against exclude patterns
                    if not any(pattern in str(file_path) for pattern in exclude_patterns):
                        files.append(file_path.resolve())
    except PermissionError:
        print(f"  Permission denied scanning: {directory}")
    except Exception as e:
        print(f"  Error scanning directory {directory}: {type(e).__name__} - {e}")
    
    return files

def create_markdown_doc(documentation: Dict, output_path: Path):
    md_lines = []
    # These main keys are expected from generate_documentation() output
    doc_file_info = documentation # The root dict is what we work with
    analysis_summary = doc_file_info.get('documentation', {}) # This is the curated summary
    metrics = doc_file_info.get('metrics', {})
    lines_metrics = metrics.get('lines', {})
    structure = doc_file_info.get('structure', {})

    md_lines.append(f"# {doc_file_info.get('file', 'N/A')}")
    md_lines.append(f"`{doc_file_info.get('path', 'N/A')}`\n")
    md_lines.append(f"**Language:** {doc_file_info.get('language','N/A')} | **Size:** {metrics.get('size',0):,} bytes | **Lines:** {lines_metrics.get('total',0)} (Code: {lines_metrics.get('code',0)}, Comments: {lines_metrics.get('comment',0)})")
    md_lines.append(f"**Category:** {analysis_summary.get('category','N/A')} | **Complexity:** {analysis_summary.get('complexity','N/A')} | **Last Analyzed:** {doc_file_info.get('last_analyzed','N/A')[:10]}")
    md_lines.append("\n## Purpose\n" + str(analysis_summary.get('summary', 'Not available.'))) # 'summary' comes from 'purpose' in AI
    if analysis_summary.get('description'): md_lines.append("\n## Description\n" + str(analysis_summary.get('description')))

    exec_info = structure.get('execution_info', {})
    if exec_info.get('command'):
        md_lines.append("\n## How to Run")
        md_lines.append(f"```bash\n{exec_info['command']}\n```")
        if exec_info.get('requires_args'): md_lines.append("*This script likely requires arguments.*")
        if exec_info.get('environment_vars'):
            md_lines.append("\n**Environment Variables:**")
            for var in exec_info['environment_vars']: md_lines.append(f"- `{var}`")
    
    if analysis_summary.get('main_functionality'):
        md_lines.append("\n## Main Functionality")
        for item in analysis_summary['main_functionality']: md_lines.append(f"- {item}")

    if structure.get('dependencies'):
        dep_analysis_text = analysis_summary.get('dependencies_analysis')
        if not dep_analysis_text: # Fallback if AI didn't provide it
            dep_analysis_text = ", ".join(list(set(structure['dependencies']))[:7]) + ('...' if len(structure['dependencies']) > 7 else '')
        md_lines.append("\n## Key Dependencies")
        md_lines.append(dep_analysis_text)

    if structure.get('functions'):
        md_lines.append("\n## Functions")
        for func in structure['functions'][:15]: # Limit displayed functions
            args_str = ", ".join([a.get('name', 'arg') + (f": {a.get('type')}" if a.get('type') else '') for a in func.get('args', [])])
            returns_str = f" -> {func.get('returns')}" if func.get('returns') else ""
            md_lines.append(f"### `def {func['name']}({args_str}){returns_str}`")
            docstring = func.get('docstring')
            if docstring: 
                first_line_doc = docstring.splitlines()[0] if '\n' in docstring else docstring
                md_lines.append(f"> {first_line_doc}\n")
            # else: md_lines.append("> No docstring.\n") # Optional: be explicit
        if len(structure['functions']) > 15: md_lines.append("\n*... and more functions.*")


    if structure.get('classes'):
        md_lines.append("\n## Classes")
        for cls in structure['classes'][:10]: # Limit displayed classes
            bases_str = f"({', '.join(cls.get('bases',[]))})" if cls.get('bases') else ""
            md_lines.append(f"### `class {cls['name']}{bases_str}`")
            docstring = cls.get('docstring')
            if docstring: 
                first_line_doc = docstring.splitlines()[0] if '\n' in docstring else docstring
                md_lines.append(f"> {first_line_doc}\n")
            # else: md_lines.append("> No docstring.\n")
            if cls.get('methods'):
                 md_lines.append("  **Methods:** " + ", ".join([f"`{m['name']}()`" for m in cls['methods'][:5]]) + ('...' if len(cls['methods']) > 5 else ''))
        if len(structure['classes']) > 10: md_lines.append("\n*... and more classes.*")


    if analysis_summary.get('usage_examples'):
        md_lines.append("\n## Usage Examples")
        for ex in analysis_summary['usage_examples']: md_lines.append(f"```\n{ex}\n```")

    potential_issues = analysis_summary.get('potential_issues', [])
    if potential_issues and potential_issues != ['None identified'] and potential_issues != [""]: # Check for non-empty lists
        md_lines.append("\n## Potential Issues / Improvements")
        for item in potential_issues: 
            if item.strip(): md_lines.append(f"- {item}") # Ensure item is not just whitespace

    try:
        with open(output_path, 'w', encoding='utf-8') as f: f.write("\n".join(md_lines))
    except Exception as e_md:
        print(f"  ✗ Error writing MD doc {output_path}: {e_md}")


def generate_project_reports(conn, scan_path: Path):
    # Placeholder: Implement project-wide reporting logic here
    # Example: Summarize languages, common dependencies, overall complexity etc.
    # You would query the database (conn) for this.
    print(f"\nPlaceholder: Project-level reports would be generated for '{scan_path}'.")
    print("This could include language distribution, top dependencies, complexity overview, etc.")
    # Example query:
    # cursor = conn.cursor()
    # cursor.execute("SELECT language, COUNT(*) as count FROM tools GROUP BY language ORDER BY count DESC")
    # lang_dist = cursor.fetchall()
    # print("\nLanguage Distribution:")
    # for lang, count in lang_dist:
    # print(f"- {lang}: {count}")


def main():
    # Parse command line arguments
    args = parse_args()
    scan_path_str = args.path
    focus_on_custom = args.custom
    skip_analysis = args.skip_analysis
    max_file_size = args.max_size
    max_workers = args.workers
    quiet_mode = args.quiet
    skip_docs = args.no_docs
    
    # Define configuration
    global TIMEOUT, MAX_OLLAMA_WORKERS, DB_PATH
    TIMEOUT = 120  # Seconds
    MAX_OLLAMA_WORKERS = max_workers
    
    # Resolve the scan path
    scan_path = Path(scan_path_str).expanduser().resolve()
    
    if not scan_path.exists():
        print(f"Error: Provided scan path does not exist: {scan_path}")
        return

    print(f"Starting Comprehensive Code Scanner...")
    print(f"Database path: {DB_PATH}")
    print(f"Scanning from: {scan_path}")
    print(f"Focus on custom code: {focus_on_custom}")
    print(f"Skip AI analysis: {skip_analysis}")
    print(f"Maximum parallel workers: {MAX_OLLAMA_WORKERS}")
    
    # Initialize database
    main_conn_for_init_and_reports = init_database() 
    if main_conn_for_init_and_reports:
         print("Database schema ensured.")
    else:
        print("Error: Could not initialize database connection.")
        return

    print("\nScanning for files...")
    # Use the appropriate scan function based on the focus parameter
    if focus_on_custom:
        # Use more aggressive filtering for custom code
        exclude_patterns = [
            '__pycache__', '.git', 'node_modules', 'venv', '.venv',
            'env', '.env', 'site-packages', 'dist', 'build', '.pytest_cache', '.tox',
            'egg-info', 'wheels', 'lib/python', 'vendor', 'cache', '.idea', '.vscode',
            'migrations', 'deps',
            '*.pyc', '*.pyo', '*.egg-info', '.DS_Store', '.*'
        ]
        all_files = scan_directory(scan_path, exclude_patterns)
    else:
        # Use default filtering
        all_files = scan_directory(scan_path)
    
    total_files_to_process = len(all_files)

    if total_files_to_process == 0:
        print("No files found to process with the current filters.")
        if main_conn_for_init_and_reports: main_conn_for_init_and_reports.close()
        return

    # Group files by project/directory for better reporting
    grouped_files = {}
    for file_path in all_files:
        # Get parent directory name as the project identifier
        parent_dir = file_path.parent.name
        # Handle special cases like 'src', 'lib' by including grandparent
        if parent_dir in ['src', 'lib', 'app', 'source']:
            grandparent = file_path.parent.parent.name
            if grandparent:
                parent_dir = f"{grandparent}/{parent_dir}"
                
        if parent_dir not in grouped_files:
            grouped_files[parent_dir] = []
        grouped_files[parent_dir].append(file_path)
    
    print(f"\nFound {total_files_to_process} files across {len(grouped_files)} directories/projects")
    
    success_count, error_count, skipped_count = 0, 0, 0
    start_time = time.time()
    
    executor_instance = None # For access in finally block for KeyboardInterrupt
    active_futures_list = [] # Keep track of futures for potential cancellation

    try:
        # Process files with thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_OLLAMA_WORKERS) as executor:
            executor_instance = executor # Assign for potential use in except/finally
            
            # Create a dictionary mapping futures to files for each project
            all_futures_to_file = {}
            
            # Display project information and submit tasks
            for project_name, project_files in sorted(grouped_files.items()):
                print(f"\nSubmitting tasks for project/directory: {project_name} ({len(project_files)} files)")
                
                # Submit tasks for this project
                project_futures = {
                    executor.submit(
                        process_single_file,
                        fp,       # file_path
                        scan_path, # scan_path_base
                        skip_analysis, # whether to skip AI analysis
                        skip_docs # whether to skip documentation generation
                    ): fp
                    for fp in project_files
                }
                
                # Add to overall tracking dict
                all_futures_to_file.update(project_futures)
            
            active_futures_list = list(all_futures_to_file.keys())
            total_futures = len(active_futures_list)
            
            print(f"\nProcessing {total_futures} files with {MAX_OLLAMA_WORKERS} workers...")
            
            processed_count_display = 0
            last_progress_update_time = start_time

            # Process results as they complete
            for future in concurrent.futures.as_completed(active_futures_list):
                file_path_processed = all_futures_to_file[future]
                
                # Construct relative path for display
                try:
                    display_name = str(file_path_processed.relative_to(scan_path))
                except ValueError:
                    display_name = file_path_processed.name

                processed_count_display += 1
                try:
                    result_status = future.result()
                    if result_status == "success":
                        success_count += 1
                        if not quiet_mode:
                            print(f"  ✓ ({processed_count_display}/{total_futures}) OK: {display_name}")
                    elif result_status.startswith("skipped"):
                        skipped_count += 1
                        if not quiet_mode:
                            print(f"  ↷ ({processed_count_display}/{total_futures}) Skip: {display_name} ({result_status.split('_',1)[1]})")
                    else: 
                        error_count += 1
                        print(f"  ✗ ({processed_count_display}/{total_futures}) Fail: {display_name} ({result_status})")
                except Exception as exc: # Exception from the worker task itself
                    error_count += 1
                    print(f"  ✗ ({processed_count_display}/{total_futures}) EXCEPTION for {display_name}: {exc}")
                
                # Show periodic progress
                current_time = time.time()
                if processed_count_display % 20 == 0 or processed_count_display == total_futures or \
                   (current_time - last_progress_update_time) > 10:
                    elapsed = current_time - start_time
                    rate = processed_count_display / elapsed if elapsed > 0 else 0
                    print(f"PROGRESS: {processed_count_display}/{total_futures} ({processed_count_display/total_futures*100:.1f}%) | "
                          f"S:{success_count} E:{error_count} K:{skipped_count} | "
                          f"Rate:{rate:.2f}f/s | Elap:{elapsed:.0f}s")
                    last_progress_update_time = current_time
        
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received. Attempting to shut down workers...")
        if executor_instance:
            # Python 3.9+ allows cancel_futures=True
            if sys.version_info >= (3, 9):
                print("Cancelling pending tasks and shutting down...")
                executor_instance.shutdown(wait=True, cancel_futures=True)
            else:
                print("Shutting down (waiting for active tasks to complete or timeout)...")
                # For older Python, try to cancel manually then shutdown
                for fut in active_futures_list:
                    if not fut.done():
                        fut.cancel()
                executor_instance.shutdown(wait=True)
        print("Workers shut down process initiated.")
    except Exception as e:
        print(f"\nAn unexpected error occurred in main processing loop: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
    finally:
        elapsed_total = time.time() - start_time
        print("\n" + "="*60 + f"\nSCAN COMPLETE for {scan_path}\n" + "="*60)
        print(f"Total Files Found: {total_files_to_process}")
        print(f"Successfully Processed & Saved: {success_count}")
        print(f"Skipped (large/empty): {skipped_count}")
        print(f"Errors/Failed Processing/DB Saves: {error_count}")
        print(f"Total Time Taken: {elapsed_total:.2f} seconds")
        if success_count > 0 and elapsed_total > 0 : 
             print(f"Average Time Per Successfully Processed File: {elapsed_total/success_count:.2f} seconds")
        
        # Generate summary reports by language, category, etc.
        if success_count > 0 and main_conn_for_init_and_reports:
            print("\nGenerating project reports...")
            generate_project_reports(main_conn_for_init_and_reports, scan_path)
        
        # Close the database connection
        if main_conn_for_init_and_reports:
            main_conn_for_init_and_reports.close()
            
if __name__ == '__main__':
    main()