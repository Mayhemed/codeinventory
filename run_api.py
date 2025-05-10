#!/usr/bin/env python
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the API
from codeinventory.api import app

if __name__ == '__main__':
    app.run(port=8000, debug=True)
