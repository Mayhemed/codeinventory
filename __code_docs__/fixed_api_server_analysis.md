# fixed_api_server.py

**Path:** `fixed_api_server.py`
**Language:** python
**Last analyzed:** 2025-05-11T02:47:54.508224

## Summary

Fixed API server that provides data to the CodeInventory app.

## Description

This code defines a Flask application that serves as an API for the CodeInventory app. It connects to a SQLite database and provides various endpoints for retrieving data related to tools, projects, insights, and other information relevant to the development process. The code uses Flask and flask-cors to handle cross-origin resource sharing (CORS) requests and sqlite3 to interact with the database.

## Metrics

- **Category:** api
- **Complexity:** moderate
- **Size:** 10,045 bytes
- **Lines:** 310 total (253 code, 57 comments)

## Dependencies

- flask
- flask_cors
- json
- os
- pathlib
- sqlite3

## Functions

### `table_exists(conn, table_name) -> None`

Check if a table exists in the database.

### `get_stats() -> None`

Get database statistics.

### `get_tools() -> None`

Get all tools.

### `get_projects() -> None`

Get project information.

### `get_insights() -> None`

Get insights and analysis.

### `health_check() -> None`

Health check endpoint.
