# enhanced_scanner.py

**Path:** `enhanced_scanner.py`
**Language:** python
**Last analyzed:** 2025-05-11T02:47:27.743629

## Summary

This code provides an enhanced scanner for Python code analysis, capable of extracting detailed information from Python source files.

## Description

The CodeAnalyzer class in this module defines a Python interface for analyzing Python code and generating documentation. It uses the Ollama model to generate documentation and provide insights into the code's structure and functionality.

## Metrics

- **Category:** utility
- **Complexity:** moderate
- **Size:** 17,690 bytes
- **Lines:** 486 total (392 code, 94 comments)

## Architectural Role

Provides a Python interface for analyzing Python code and generating documentation.

## Dependencies

- ast
- datetime
- hashlib
- json
- os
- pathlib
- re
- requests
- sqlite3
- time

## Functions

### `get_file_info(filepath) -> None`

Get basic file information.

### `get_language(filepath) -> None`

Determine file language from extension.

### `analyze_with_ollama(file_info, structure_info) -> None`

Get high-level analysis from Ollama.

### `generate_documentation(file_info, structure_info, ollama_analysis) -> None`

Generate comprehensive documentation.

### `init_db() -> None`

Initialize the database with enhanced schema.

### `save_to_db(conn, file_info, structure_info, ollama_analysis, documentation) -> None`

Save enhanced analysis to database.

### `analyze_project_structure(root_path) -> None`

Analyze overall project structure.

### `main() -> None`

### `__init__(self) -> None`

### `analyze_python_code(self, code) -> None`

Extract detailed information from Python code.

## Classes

### `CodeAnalyzer`

**Methods:**
- `__init__`
- `analyze_python_code`

## Potential Issues

- External dependency on the Ollama model may affect performance or availability

## Performance Notes

Performance may be affected by the size of the code being analyzed and the complexity of the analysis.
