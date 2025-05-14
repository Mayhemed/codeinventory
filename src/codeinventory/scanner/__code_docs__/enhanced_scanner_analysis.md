# enhanced_scanner.py

**Path:** `src/codeinventory/scanner/enhanced_scanner.py`
**Language:** python
**Last analyzed:** 2025-05-11T02:53:04.589171

## Summary

This code is an enhanced scanner that analyzes Python files for execution and import patterns.

## Description

The EnhancedAnalyzer class provides a comprehensive analysis of Python files by identifying their execution command, importable items, requires_args flag, environment variables, dependencies, and more. It can also analyze JavaScript, TypeScript, and shell scripts.

## Metrics

- **Category:** utility
- **Complexity:** moderate
- **Size:** 7,613 bytes
- **Lines:** 206 total (153 code, 53 comments)

## Architectural Role

This code provides a centralized function for analyzing Python files, making it a valuable utility for any project that involves parsing and analyzing Python source code.

## Dependencies

- ast
- pathlib
- re
- typing

## Functions

### `__init__(self) -> None`

### `analyze_file(self, file_path, content, language) -> Dict`

Analyze a file for execution and import information.

### `analyze_python(self, file_path, content) -> Dict`

Analyze Python file for execution and import patterns.

### `analyze_javascript(self, file_path, content) -> Dict`

Analyze JavaScript file for execution patterns.

### `analyze_shell(self, file_path, content) -> Dict`

Analyze shell script for execution patterns.

## Classes

### `EnhancedAnalyzer`

**Methods:**
- `__init__`
- `analyze_file`
- `analyze_python`
- `analyze_javascript`
- `analyze_shell`

## Performance Notes

The code uses regular expressions for parsing Python files, which may result in slower performance compared to other analysis methods. However, it provides a comprehensive set of features and can be optimized further by using faster regex libraries or alternative analysis methods.
