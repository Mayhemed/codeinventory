"""Tests for the enhanced scanner functionality."""
import pytest
from pathlib import Path
from codeinventory.scanner.enhanced_scanner import EnhancedAnalyzer

class TestEnhancedAnalyzer:
    def test_analyze_python_with_main(self):
        """Test analyzing Python file with main guard."""
        analyzer = EnhancedAnalyzer()
        
        python_code = '''#!/usr/bin/env python
import argparse
import os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    args = parser.parse_args()
    print(f"Processing {args.input}")

if __name__ == "__main__":
    main()
'''
        result = analyzer.analyze_python('/test/script.py', python_code)
        
        assert result['execution_command'] == 'python script.py -h'
        assert result['requires_args'] == True
        assert 'argparse' in result['dependencies']
    
    def test_analyze_python_with_click(self):
        """Test analyzing Python file with click CLI."""
        analyzer = EnhancedAnalyzer()
        
        python_code = '''#!/usr/bin/env python
import click

@click.command()
@click.option('--count', default=1, help='Number of greetings.')
def hello(count):
    """Simple program that greets NAME for a total of COUNT times."""
    for x in range(count):
        click.echo('Hello!')

if __name__ == '__main__':
    hello()
'''
        result = analyzer.analyze_python('/test/click_script.py', python_code)
        
        assert result['execution_command'] == 'python click_script.py --help'
        assert result['requires_args'] == True
        assert 'click' in result['dependencies']
    
    def test_analyze_python_importable(self):
        """Test analyzing Python file for importable items."""
        analyzer = EnhancedAnalyzer()
        
        python_code = '''"""Utility functions for data processing."""

def process_data(data):
    """Process input data."""
    return data.upper()

class DataProcessor:
    """A class for processing data."""
    
    def __init__(self):
        self.data = []
    
    def add_data(self, item):
        """Add item to data."""
        self.data.append(item)

def _private_function():
    """This should not be importable."""
    pass
'''
        result = analyzer.analyze_python('/test/utils.py', python_code)
        
        assert len(result['importable_items']['functions']) == 1
        assert result['importable_items']['functions'][0]['name'] == 'process_data'
        assert len(result['importable_items']['classes']) == 1
        assert result['importable_items']['classes'][0]['name'] == 'DataProcessor'
    
    def test_analyze_javascript_node(self):
        """Test analyzing Node.js file."""
        analyzer = EnhancedAnalyzer()
        
        js_code = '''const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;

app.get('/', (req, res) => {
    res.send('Hello World!');
});

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});

module.exports = app;
'''
        result = analyzer.analyze_javascript('/test/server.js', js_code)
        
        assert result['execution_command'] == 'node server.js'
        assert 'PORT' in result['environment_vars']
        assert 'app' in result['importable_items']
    
    def test_analyze_shell_script(self):
        """Test analyzing shell script."""
        analyzer = EnhancedAnalyzer()
        
        shell_code = '''#!/bin/bash
# Process files script

if [ $# -eq 0 ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

DIRECTORY=$1
OUTPUT_DIR=${OUTPUT_DIR:-./output}

for file in "$DIRECTORY"/*; do
    process_file "$file" > "$OUTPUT_DIR/$(basename "$file").out"
done
'''
        result = analyzer.analyze_shell('/test/process.sh', shell_code)
        
        assert result['execution_command'] == './process.sh [args]'
        assert result['requires_args'] == True
        assert 'OUTPUT_DIR' in result['environment_vars']
