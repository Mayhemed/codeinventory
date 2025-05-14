#!/usr/bin/env python
"""Test runner to check what's working and what's not in CodeInventory."""
import sys
import subprocess
import json
from pathlib import Path
import sqlite3
import yaml

class CodeInventoryTester:
    def __init__(self):
        self.results = {
            'working': [],
            'failing': [],
            'partial': []
        }
    
    def test_installation(self):
        """Test that the package is properly installed."""
        try:
            import codeinventory
            self.results['working'].append('Package Installation')
        except ImportError as e:
            self.results['failing'].append(('Package Installation', str(e)))
    
    def test_cli_available(self):
        """Test that CLI is available."""
        try:
            result = subprocess.run(['python', '-m', 'codeinventory.cli.cli', '--help'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.results['working'].append('CLI Available')
            else:
                self.results['failing'].append(('CLI Available', result.stderr))
        except Exception as e:
            self.results['failing'].append(('CLI Available', str(e)))
    
    def test_database(self):
        """Test database functionality."""
        try:
            # Load config to get DB path
            config_path = Path('src/codeinventory/config/default.yaml')
            with open(config_path) as f:
                config = yaml.safe_load(f)
            
            db_path = Path(config['database']['path']).expanduser()
            
            # Check if database exists
            if db_path.exists():
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Check tables exist
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                required_tables = ['tools', 'components', 'dependencies', 'relationships']
                missing_tables = [t for t in required_tables if t not in tables]
                
                if missing_tables:
                    self.results['partial'].append(('Database Schema', f'Missing tables: {missing_tables}'))
                else:
                    self.results['working'].append('Database Schema')
                
                # Check for new columns
                cursor.execute("PRAGMA table_info(tools)")
                columns = [col[1] for col in cursor.fetchall()]
                
                required_columns = ['execution_command', 'requires_args', 'environment_vars', 'importable_items']
                missing_columns = [c for c in required_columns if c not in columns]
                
                if missing_columns:
                    self.results['partial'].append(('Database Columns', f'Missing columns: {missing_columns}'))
                else:
                    self.results['working'].append('Database Columns')
                
                conn.close()
            else:
                self.results['failing'].append(('Database', 'Database file not found'))
        except Exception as e:
            self.results['failing'].append(('Database', str(e)))
    
    def test_ollama_connection(self):
        """Test Ollama connectivity."""
        try:
            import requests
            response = requests.get('http://localhost:11434/api/version', timeout=5)
            if response.status_code == 200:
                self.results['working'].append('Ollama Connection')
                
                # Check if codellama model is available
                models_response = requests.get('http://localhost:11434/api/tags')
                if models_response.status_code == 200:
                    models = models_response.json().get('models', [])
                    if any('codellama' in model.get('name', '') for model in models):
                        self.results['working'].append('Codellama Model')
                    else:
                        self.results['failing'].append(('Codellama Model', 'Model not found'))
            else:
                self.results['failing'].append(('Ollama Connection', f'Status code: {response.status_code}'))
        except Exception as e:
            self.results['failing'].append(('Ollama Connection', str(e)))
    
    def test_api_server(self):
        """Test API server functionality."""
        try:
            import requests
            # Try on port 8001 (from your fixed_api.py)
            response = requests.get('http://127.0.0.1:8001/api/stats', timeout=5)
            if response.status_code == 200:
                self.results['working'].append('API Server')
                
                # Test specific endpoints
                endpoints = ['/api/tools', '/api/components', '/api/relationships']
                for endpoint in endpoints:
                    try:
                        resp = requests.get(f'http://127.0.0.1:8001{endpoint}', timeout=5)
                        if resp.status_code == 200:
                            self.results['working'].append(f'API Endpoint: {endpoint}')
                        else:
                            self.results['failing'].append((f'API Endpoint: {endpoint}', f'Status: {resp.status_code}'))
                    except Exception as e:
                        self.results['failing'].append((f'API Endpoint: {endpoint}', str(e)))
            else:
                self.results['failing'].append(('API Server', 'Not running on port 8001'))
        except Exception as e:
            self.results['failing'].append(('API Server', 'Not running'))
    
    def test_dashboard_files(self):
        """Test dashboard files exist."""
        dashboard_files = [
            'dashboard/index.html',
            'dashboard/main.js',
            'dashboard/renderer.js',
            'dashboard/styles.css',
            'dashboard/package.json'
        ]
        
        for file_path in dashboard_files:
            path = Path(file_path)
            if path.exists():
                self.results['working'].append(f'Dashboard File: {file_path}')
            else:
                self.results['failing'].append((f'Dashboard File: {file_path}', 'File not found'))
    
    def test_enhanced_scanner(self):
        """Test enhanced scanner functionality."""
        try:
            from codeinventory.scanner.enhanced_scanner import EnhancedAnalyzer
            analyzer = EnhancedAnalyzer()
            
            # Test simple Python code
            test_code = '''def test(): pass
if __name__ == "__main__":
    test()'''
            
            result = analyzer.analyze_python('test.py', test_code)
            if result and 'execution_command' in result:
                self.results['working'].append('Enhanced Scanner')
            else:
                self.results['partial'].append(('Enhanced Scanner', 'Limited functionality'))
        except Exception as e:
            self.results['failing'].append(('Enhanced Scanner', str(e)))
    
    def test_config_loading(self):
        """Test configuration loading."""
        try:
            config_path = Path('src/codeinventory/config/default.yaml')
            if config_path.exists():
                with open(config_path) as f:
                    config = yaml.safe_load(f)
                
                required_sections = ['scanner', 'analyzer', 'database']
                missing_sections = [s for s in required_sections if s not in config]
                
                if missing_sections:
                    self.results['partial'].append(('Configuration', f'Missing sections: {missing_sections}'))
                else:
                    self.results['working'].append('Configuration')
            else:
                self.results['failing'].append(('Configuration', 'Config file not found'))
        except Exception as e:
            self.results['failing'].append(('Configuration', str(e)))
    
    def run_all_tests(self):
        """Run all tests and generate report."""
        print("🔍 Testing CodeInventory Components...")
        print("=" * 50)
        
        self.test_installation()
        self.test_cli_available()
        self.test_database()
        self.test_ollama_connection()
        self.test_api_server()
        self.test_dashboard_files()
        self.test_enhanced_scanner()
        self.test_config_loading()
        
        # Generate report
        print("\n✅ WORKING:")
        for item in self.results['working']:
            print(f"  - {item}")
        
        print("\n⚠️  PARTIALLY WORKING:")
        for item, issue in self.results['partial']:
            print(f"  - {item}: {issue}")
        
        print("\n❌ NOT WORKING:")
        for item, error in self.results['failing']:
            print(f"  - {item}: {error}")
        
        # Summary
        total = len(self.results['working']) + len(self.results['partial']) + len(self.results['failing'])
        working_pct = (len(self.results['working']) / total * 100) if total > 0 else 0
        
        print(f"\n📊 SUMMARY:")
        print(f"  Total components tested: {total}")
        print(f"  Working: {len(self.results['working'])} ({working_pct:.1f}%)")
        print(f"  Partially working: {len(self.results['partial'])}")
        print(f"  Not working: {len(self.results['failing'])}")
        
        return self.results

if __name__ == "__main__":
    tester = CodeInventoryTester()
    results = tester.run_all_tests()
    
    # Save results to file
    with open('test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\nDetailed results saved to test_results.json")
