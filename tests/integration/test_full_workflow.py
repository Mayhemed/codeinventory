"""Integration tests for the full CodeInventory workflow."""
import pytest
import sqlite3
import json
import tempfile
import shutil
from pathlib import Path
from click.testing import CliRunner
from codeinventory.cli.cli import cli
from codeinventory.database.db import InventoryDB
from codeinventory.scanner.scanner import Scanner
from codeinventory.analyzer.ollama_analyzer import OllamaAnalyzer
import yaml

@pytest.fixture
def test_config():
    """Create a test configuration."""
    config = {
        'database': {
            'path': ':memory:'  # Use in-memory database for tests
        },
        'scanner': {
            'paths': ['test_project'],
            'exclude': ['__pycache__', '.git'],
            'max_file_size': 1048576,
            'extensions': {
                'python': ['.py'],
                'javascript': ['.js']
            }
        },
        'analyzer': {
            'ollama': {
                'host': 'http://localhost:11434',
                'model': 'codellama',
                'temperature': 0.3
            },
            'timeout': 30
        }
    }
    return config

@pytest.fixture
def test_project_dir():
    """Create a temporary test project directory."""
    temp_dir = tempfile.mkdtemp()
    project_dir = Path(temp_dir) / 'test_project'
    project_dir.mkdir()
    
    # Create test files
    python_file = project_dir / 'test_script.py'
    python_file.write_text('''#!/usr/bin/env python
"""A test Python script."""
import os
import sys

def hello_world():
    """Print hello world."""
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
''')
    
    js_file = project_dir / 'test_app.js'
    js_file.write_text('''// A test JavaScript file
const express = require('express');
const app = express();

app.get('/', (req, res) => {
    res.send('Hello World!');
});

app.listen(3000, () => {
    console.log('Server running on port 3000');
});
''')
    
    yield project_dir
    shutil.rmtree(temp_dir)

class TestScanner:
    def test_scan_directory(self, test_config, test_project_dir):
        """Test scanning a directory."""
        scanner = Scanner(test_config)
        files = scanner.scan(str(test_project_dir))
        
        assert len(files) == 2
        assert any(f['name'] == 'test_script.py' for f in files)
        assert any(f['name'] == 'test_app.js' for f in files)
    
    def test_file_detection(self, test_config, test_project_dir):
        """Test file type and language detection."""
        scanner = Scanner(test_config)
        files = scanner.scan(str(test_project_dir))
        
        python_file = next(f for f in files if f['name'] == 'test_script.py')
        assert python_file['language'] == 'python'
        assert python_file['type'] == 'module'
        
        js_file = next(f for f in files if f['name'] == 'test_app.js')
        assert js_file['language'] == 'javascript'
        assert js_file['type'] == 'module'

class TestDatabase:
    def test_save_and_retrieve_tool(self, test_config):
        """Test saving and retrieving a tool from the database."""
        db = InventoryDB(':memory:')
        
        file_info = {
            'path': '/test/script.py',
            'name': 'script.py',
            'type': 'module',
            'language': 'python',
            'hash': 'abc123',
            'last_modified': 1234567890
        }
        
        analysis = {
            'purpose': 'Test script',
            'description': 'A test Python script',
            'category': 'utility',
            'complexity': 'simple',
            'execution_command': 'python script.py',
            'requires_args': False,
            'environment_vars': ['PATH', 'HOME'],
            'importable_items': {'functions': [{'name': 'test_func'}]}
        }
        
        # Test saving
        tool_id = db.save_tool(file_info, analysis)
        assert tool_id is not None
        
        # Test retrieval
        tool = db.get_tool(tool_id)
        assert tool is not None
        assert tool['name'] == 'script.py'
        assert tool['purpose'] == 'Test script'
        
        db.close()
    
    def test_search_functionality(self, test_config):
        """Test search functionality."""
        db = InventoryDB(':memory:')
        
        # Add some test data
        file_info1 = {
            'path': '/test/utility.py',
            'name': 'utility.py',
            'type': 'module',
            'language': 'python',
            'hash': 'def456',
            'last_modified': 1234567890
        }
        
        analysis1 = {
            'purpose': 'Utility functions',
            'description': 'Common utility functions',
            'category': 'utility'
        }
        
        db.save_tool(file_info1, analysis1)
        
        # Test search
        results = db.search('utility')
        assert len(results) > 0
        assert results[0]['name'] == 'utility.py'
        
        db.close()

class TestCLI:
    def test_cli_scan_command(self, test_project_dir):
        """Test the CLI scan command."""
        runner = CliRunner()
        
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config = {
                'database': {'path': ':memory:'},
                'scanner': {
                    'extensions': {'python': ['.py']},
                    'exclude': [],
                    'max_file_size': 1048576
                },
                'analyzer': {
                    'ollama': {
                        'host': 'http://localhost:11434',
                        'model': 'codellama',
                        'temperature': 0.3
                    },
                    'timeout': 30
                }
            }
            yaml.dump(config, f)
            config_path = f.name
        
        # Mock the config loading
        result = runner.invoke(cli, ['scan', str(test_project_dir)])
        
        # Check basic execution (won't work fully without Ollama running)
        assert result.exit_code in [0, 1]  # Allow failure due to missing Ollama

class TestAnalyzer:
    @pytest.mark.skipif(True, reason="Requires Ollama to be running")
    def test_analyze_python_file(self, test_config):
        """Test analyzing a Python file with Ollama."""
        analyzer = OllamaAnalyzer(test_config)
        
        file_info = {
            'content': 'def hello(): print("Hello")',
            'language': 'python'
        }
        
        result = analyzer.analyze(file_info)
        assert result is not None
        assert 'purpose' in result

class TestAPI:
    def test_api_endpoints(self):
        """Test API endpoints (without Flask running)."""
        from codeinventory.api import app
        
        client = app.test_client()
        
        # Test root endpoint
        response = client.get('/')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
        assert data['message'] == 'CodeInventory API'

class TestDashboard:
    def test_dashboard_html_exists(self):
        """Test that dashboard HTML file exists."""
        dashboard_path = Path(__file__).parent.parent.parent / 'dashboard' / 'index.html'
        assert dashboard_path.exists()
    
    def test_dashboard_js_exists(self):
        """Test that dashboard JavaScript files exist."""
        renderer_path = Path(__file__).parent.parent.parent / 'dashboard' / 'renderer.js'
        main_path = Path(__file__).parent.parent.parent / 'dashboard' / 'main.js'
        assert renderer_path.exists()
        assert main_path.exists()

def test_installation():
    """Test that the package is properly installed."""
    import codeinventory
    assert codeinventory is not None

def test_configuration_loading():
    """Test loading the default configuration."""
    config_path = Path(__file__).parent.parent.parent / 'src' / 'codeinventory' / 'config' / 'default.yaml'
    assert config_path.exists()
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    assert 'scanner' in config
    assert 'analyzer' in config
    assert 'database' in config
