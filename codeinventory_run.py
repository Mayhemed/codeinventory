#!/usr/bin/env python
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from codeinventory.cli.cli import main

if __name__ == '__main__':
    main()
