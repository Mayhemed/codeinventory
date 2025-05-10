import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from codeinventory.api import app

if __name__ == '__main__':
    app.run(port=8001, debug=True)
