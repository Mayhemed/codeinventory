# scanner.py

**Path:** `src/codeinventory/scanner/scanner.py`
**Language:** python
**Last analyzed:** 2025-05-11T02:53:18.344938

## Summary

Scan a directory for code files using a configuration file.

## Description

This module provides a class called Scanner that can be initialized with a config dictionary containing a 'scanner' key and its corresponding value is a dictionary of parameters used to configure the scanning process. The supported extensions are specified under the 'extensions' key in the config, and the exclude pattern is specified under the 'exclude' key. The scan method takes a directory path as an argument and returns a list of dictionaries containing information about each found file.

## Metrics

- **Category:** data-processing
- **Complexity:** moderate
- **Size:** 3,666 bytes
- **Lines:** 112 total (89 code, 23 comments)

## Architectural Role

file scanner

## Dependencies

- datetime
- glob
- hashlib
- mimetypes
- os
- pathlib
- typing

## Functions

### `__init__(self, config) -> None`

### `scan(self, directory) -> List[Dict]`

Scan directory for code files.

### `_find_files(self, directory) -> List[Path]`

Find all supported files in directory.

### `_is_supported(self, file_path) -> bool`

Check if file extension is supported.

### `_process_file(self, file_path) -> Optional[Dict]`

Process a single file.

### `_detect_type(self, file_path) -> str`

Detect file type.

### `_detect_language(self, file_path) -> str`

Detect programming language.

## Classes

### `Scanner`

**Methods:**
- `__init__`
- `scan`
- `_find_files`
- `_is_supported`
- `_process_file`
- `_detect_type`
- `_detect_language`

## Potential Issues

- exclusion of files based on a list of patterns
- error handling for processing files and skipping invalid or unsupported files

## Security Considerations

- exclusion of files based on a list of patterns may lead to false positives or negatives

## Performance Notes

moderate, depends on the number of files in the directory and the complexity of the exclude pattern
