# Create a properly formatted README
cat > README.md << 'README'
# CodeInventory

An AI-powered code inventory system that helps you discover, understand, and manage your personal codebase.

## Features

- 🔍 **Automatic Code Discovery**: Scans directories to find all your scripts and programs
- 🤖 **AI-Powered Analysis**: Uses local AI (Ollama) to understand what your code does
- 🔗 **Relationship Mapping**: Visualizes connections between your tools
- 🔄 **Component Reusability**: Identifies reusable functions and patterns
- 🖥️ **Visual Dashboard**: Electron-based UI for exploring your code inventory
- 🔐 **Privacy-First**: All processing happens locally on your machine

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- [Ollama](https://ollama.ai/) with `codellama` model
- Node.js 18+ (for dashboard)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd codeinventory
Install Python dependencies:
uv install

Install dashboard dependencies:
 cd dashboard
npm install
cd ..

Start Ollama with codellama:
 ollama pull codellama
ollama serve


Usage
Command Line Interface
Scan a directory:
 codeinventory scan ~/Projects
Search your inventory:
 codeinventory search "file operations"
Show tool details:
 codeinventory show <tool-id>
Dashboard
Start the dashboard:
 npm run dashboard
Or start the API server and dashboard separately:
# Terminal 1: Start API server
python -m codeinventory.api

# Terminal 2: Start Electron dashboard
cd dashboard
npm start
Configuration
Edit src/codeinventory/config/default.yaml to customize:

Scan paths and exclusions
Ollama settings
File size limits
Database location

Architecture

Scanner: Finds and reads code files
Analyzer: Uses Ollama to understand code purpose and structure
Database: SQLite with full-text search
API: Flask server for dashboard
Dashboard: Electron app with visualization

Development
Run tests:
pytest tests/
License
MIT License - see LICENSE file for details
README
Create LICENSE
cat > LICENSE << 'LICENSE'
MIT License
Copyright (c) 2024 CodeInventory
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
LICENSE
# Install Python dependencies with uv
echo "Installing Python dependencies..."
uv sync
Install Node dependencies for dashboard
echo "Installing dashboard dependencies..."
cd dashboard
npm install
cd ..
# Create initial commit
git add .
git commit -m "Initial commit: CodeInventory - AI-powered code inventory system"
echo "✅ CodeInventory project created successfully!"
echo ""
echo "Next steps:"
echo "1. Ensure Ollama is running with codellama model"
echo "2. Run 'codeinventory scan ~/Projects' to scan your code"
echo "3. Run 'npm run dashboard' to start the visual dashboard"
echo ""
echo "Project location: $(pwd)"
EOF
Make the setup script executable
chmod +x setup-codeinventory.sh
echo "Setup script created! Run it with:"
echo "./setup-codeinventory.sh"

This script creates a complete CodeInventory project with:

1. **Python implementation** using `uv` for package management
2. **SQLite database** for efficient storage and search
3. **Ollama integration** for local AI analysis
4. **Electron dashboard** for visualization
5. **Full-text search** capabilities
6. **Git repository** initialization and first commit

The project structure includes:
- Scanner module for finding code files
- Analyzer module using Ollama for AI analysis
- Database module with SQLite and FTS
- CLI interface with `click` and `rich`
- Electron dashboard with network visualization
- API server using Flask

To use the script:
```
./setup-codeinventory.sh