# CodeInventory 2.0 - Improved Design

## Current Issues
Based on the code analysis, here are the main issues:
1. Complex setup requiring multiple services (Ollama, Flask API, Electron)
2. Database schema mismatches between code and actual schema
3. Poor error handling and user feedback
4. Limited functionality in the dashboard
5. Confusing workflow for first-time users

## Proposed Improvements

### 1. Simplified Architecture

```
codeinventory/
├── src/codeinventory/
│   ├── __init__.py
│   ├── main.py              # Single entry point
│   ├── core/
│   │   ├── scanner.py       # File discovery
│   │   ├── analyzer.py      # Code analysis
│   │   ├── database.py      # Data storage
│   │   └── search.py        # Search functionality
│   ├── ui/
│   │   ├── cli.py          # CLI interface
│   │   └── web.py          # Web interface (Flask)
│   └── config/
│       └── settings.py      # Configuration management
└── web/
    ├── templates/           # HTML templates
    └── static/             # CSS, JS, images
```

### 2. User-Friendly CLI

```bash
# Simple commands that work out of the box
codeinventory init          # Initialize in current directory
codeinventory scan          # Scan current directory
codeinventory search "term" # Search your inventory
codeinventory web           # Start web interface
```

### 3. Integrated Web Interface

Instead of separate Electron app, use a simple Flask web interface:
- Single command to start
- No separate API server needed
- Real-time updates via WebSocket
- Works in any browser

### 4. Smart Code Analysis

Replace Ollama dependency with built-in analysis:
- AST-based analysis for supported languages
- Pattern matching for common frameworks
- Fallback to regex-based analysis
- Optional AI enhancement (not required)

### 5. Better Database Management

- Automatic schema migrations
- Better error handling
- Export/import functionality
- Backup/restore capabilities

### 6. Interactive Setup Wizard

```python
# First-time setup
$ codeinventory init

Welcome to CodeInventory! Let's set up your code inventory.

📁 Where should we store your inventory database?
   [~/.codeinventory/inventory.db] > 

🔍 Which directories should we scan? (comma-separated)
   [~/Projects] > ~/Projects, ~/Scripts

🚫 Any directories to exclude? (comma-separated)
   [node_modules, .git, __pycache__] > 

🤖 Do you have Ollama installed for AI analysis? (y/N)
   [N] > 

✨ Setup complete! Run 'codeinventory scan' to start indexing your code.
```

### 7. Improved Dashboard Features

- **Project Overview**: Grouped by project/repository
- **Quick Actions**: Run, edit, copy commands
- **Smart Search**: Natural language queries
- **Code Snippets**: Copy importable code
- **Execution History**: Track what you've run
- **Tags & Categories**: Manual organization
- **Export Options**: Markdown, JSON, CSV

## Implementation Plan

### Phase 1: Core Functionality (Week 1)
- [ ] Rewrite database layer with proper schema
- [ ] Implement AST-based analyzer
- [ ] Create unified CLI entry point
- [ ] Add configuration management

### Phase 2: Web Interface (Week 2)
- [ ] Build Flask-based web UI
- [ ] Add real-time search
- [ ] Implement project grouping
- [ ] Create execution tracking

### Phase 3: Enhanced Features (Week 3)
- [ ] Add tagging system
- [ ] Implement export functionality
- [ ] Create backup/restore
- [ ] Add usage analytics

### Phase 4: Polish & Testing (Week 4)
- [ ] Comprehensive test suite
- [ ] Documentation
- [ ] Installation packages
- [ ] Demo videos

## Migration Path

For existing users:
1. Backup existing database
2. Run migration tool
3. Update configuration
4. Re-scan if needed

## Example Usage Scenarios

### 1. Developer Starting New Project
```bash
codeinventory search "file upload"
# Shows all your existing file upload implementations

codeinventory show upload_handler.py
# Shows details, usage examples, and copy-paste code
```

### 2. Code Reuse
```bash
codeinventory search "api client" --language python
# Find all Python API clients you've written

codeinventory export "api client" --format markdown
# Export documentation for reuse
```

### 3. Learning from Past Projects
```bash
codeinventory web
# Open dashboard
# Browse by category: "Machine Learning"
# See all ML projects with examples
```

## Success Metrics

1. **Setup Time**: < 5 minutes from install to first scan
2. **Search Speed**: < 100ms for most queries
3. **Accuracy**: 90%+ correct categorization
4. **User Retention**: 70%+ weekly active usage

## Next Steps

1. Create proof-of-concept for new architecture
2. Get user feedback on proposed changes
3. Begin incremental migration
4. Release beta version for testing
