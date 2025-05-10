import pytest
from pathlib import Path
from codeinventory.scanner.scanner import Scanner

def test_scanner_initialization():
   config = {
       'scanner': {
           'extensions': {
               'python': ['.py'],
               'javascript': ['.js']
           },
           'exclude': ['__pycache__'],
           'max_file_size': 1048576
       }
   }
   scanner = Scanner(config)
   assert scanner.supported_extensions == {'.py', '.js'}

def test_is_supported():
   config = {
       'scanner': {
           'extensions': {
               'python': ['.py'],
               'javascript': ['.js']
           },
           'exclude': [],
           'max_file_size': 1048576
       }
   }
   scanner = Scanner(config)
   
   assert scanner._is_supported(Path('test.py'))
   assert scanner._is_supported(Path('test.js'))
   assert not scanner._is_supported(Path('test.txt'))
