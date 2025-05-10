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
bashuv install

Install dashboard dependencies:
bashcd dashboard
npm install
cd ..

Start Ollama with codellama:
bashollama pull codellama
ollama serve


Usage
Command Line Interface
Scan a directory:
bashcodeinventory scan ~/Projects
Search your inventory:
bashcodeinventory search "file operations"
Show tool details:
bashcodeinventory show <tool-id>
Dashboard
Start the dashboard:
bashnpm run dashboard
Or start the API server and dashboard separately:
bash# Terminal 1: Start API server
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
bashpytest tests/
License
MIT License - see LICENSE file for details
