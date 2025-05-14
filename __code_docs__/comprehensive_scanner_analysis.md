# comprehensive_scanner.py

**Path:** `comprehensive_scanner.py`
**Language:** python
**Last analyzed:** 2025-05-11T02:50:34.739544

## Summary

This code serves as an example of comprehensive code analysis using Ollama.

## Description

The CodeAnalyzer class provides a comprehensive analysis of Python code, including extracting information from module docstrings and identifying external dependencies. The analyze_python_code() method parses the code using ast.parse(), then walks through the abstract syntax tree to identify various aspects of the code's functionality, such as imports, functions, classes, global variables, constants, decorators, and docstrings.

## Metrics

- **Category:** model
- **Complexity:** moderate
- **Size:** 46,180 bytes
- **Lines:** 1243 total (1003 code, 240 comments)

## Architectural Role

Code analyzer

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
- sys
- time
- traceback
- typing

## Functions

### `get_file_info(filepath) -> None`

Get comprehensive file information.

### `get_language(filepath) -> None`

Determine file language from extension.

### `analyze_with_ollama(file_info, structure_info) -> None`

Get comprehensive AI analysis with better prompts.

### `extract_fields_fallback(text) -> None`

Fallback method to extract fields from malformed JSON.

### `generate_enhanced_analysis(file_info, structure_info) -> None`

Generate enhanced analysis without AI.

### `generate_documentation(file_info, structure_info, analysis) -> None`

Generate comprehensive documentation.

### `init_database() -> None`

Initialize database with comprehensive schema.

### `save_to_db(conn, file_info, structure_info, analysis, documentation) -> None`

Save comprehensive analysis to database.

### `scan_directory(directory, exclude_patterns) -> List[Path]`

Recursively scan directory for files.

### `main() -> None`

### `create_markdown_doc(documentation, output_path) -> None`

Create a comprehensive markdown documentation file.

### `generate_project_reports(conn, scan_path) -> None`

Generate comprehensive project reports.

### `create_project_markdown_report(report, output_path) -> None`

Create a comprehensive markdown project report.

### `create_dependency_graph(conn, output_path) -> None`

Create a dependency graph data file.

### `__init__(self) -> None`

### `reset(self) -> None`

### `analyze_python_code(self, code) -> None`

Extract comprehensive information from Python code.

### `_extract_function_info(self, node) -> None`

Extract detailed function information.

### `_extract_class_info(self, node) -> None`

Extract detailed class information.

### `_get_decorator_name(self, decorator) -> None`

Extract decorator name.

### `_calculate_complexity(self, node) -> None`

Calculate cyclomatic complexity.

## Classes

### `CodeAnalyzer`

**Methods:**
- `__init__`
- `reset`
- `analyze_python_code`
- `_extract_function_info`
- `_extract_class_info`
- `_get_decorator_name`
- `_calculate_complexity`

## Performance Notes

The performance of this code can be optimized by caching the results of previous analyses or using faster methods for extracting information from module docstrings.
