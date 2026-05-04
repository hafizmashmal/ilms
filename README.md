# ILMS (Integrated Laboratory Management System)

## Project Overview

ILMS is a lightweight, terminal-based Integrated Laboratory Management System implemented in Python. It provides basic laboratory workflows including user and role management, patient registration, test management, invoicing, attendance and payroll, leave management, inventory, equipment logs, and reporting.

This repository contains the core application, a database initialization layer, SQL schema and query definitions, and helper modules.

## Features

- User and role management with permission controls
- Patient and test management (test groups, specimens)
- Invoicing and invoice-test associations
- Attendance, payroll and leave management
- Inventory and equipment logs
- Reporting and analytics views
- Database initialization and seeding scripts

## Requirements

- Python 3.10+ (tested with 3.10–3.11)
- Recommended: virtual environment (venv or pyenv)
- MySQL server (8.0+ recommended) or compatible (InnoDB engine required for foreign keys)
- Python packages listed in `requirements.txt` (install using pip)

## Python environment setup

1. Create and activate a virtual environment:

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Windows (cmd):

```cmd
python -m venv .venv
.\.venv\Scripts\activate
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Upgrade pip and install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

3. Optional: run a quick syntax check

```bash
python -m pyflakes .
```

## Environment variables

The application reads sensitive configuration (database credentials, encryption key) from environment variables. Set these before running the app.

- `ILMS_DB_HOST` - database host (default provided in code)
- `ILMS_DB_PORT` - database port (default 3306)
- `ILMS_DB_NAME` - database name created/used by the app
- `ILMS_DB_USER` - DB username
- `ILMS_DB_PASSWORD` - DB user password
- `ILMS_ENCRYPTION_KEY` - optional symmetric key for `DataEncryptor` (defaults to an internal value if not set)

Example (PowerShell):

```powershell
$env:ILMS_DB_HOST = "127.0.0.1"
$env:ILMS_DB_USER = "ilms_user"
$env:ILMS_DB_PASSWORD = "secret"
$env:ILMS_DB_NAME = "ilms_db"
$env:ILMS_ENCRYPTION_KEY = "my_super_secret_key"
```

## Database initialization

The application attempts to create the database and required tables automatically on first run via `DatabaseManager` in `database.py`. It executes the SQL statements located in `sql_queries.py` and seeds initial data if missing.

If you prefer to manage the database manually, use the SQL in `sql_queries.py` to create tables, views, stored procedures, triggers and sample DML. Multi-statement objects like procedures should be executed with a client that supports multi-statement execution.

## Running the application

This project contains a curses-based console UI. Run the main entrypoint:

```bash
python ilms.py
```

Notes:
- The console UI uses `curses` and may behave differently on Windows. Use a terminal that supports curses (e.g., Windows Subsystem for Linux, or a compatible terminal emulator). A fallback non-curses runner may not be included.
- If the DB is remote, ensure network connectivity and proper firewall rules.

## Tests

A minimal `test.py` exists for quick checks. Run it with:

```bash
python test.py
```

Add unit and integration tests as needed.

## Security & Deployment

- Do not store production passwords in source. Use environment variables or a secrets manager.
- Use TLS for DB connections if supported and the DB is remote.
- Restrict database user privileges (avoid using root).
- Rotate `ILMS_ENCRYPTION_KEY` and DB passwords periodically.

## Contributing

Contributions are welcome. Please open issues or submit pull requests.

## Files of interest

- `ilms.py` - main application and UI
- `database.py` - DB manager, initialization and utilities
- `database_operations.py` - higher-level CRUD operations
- `sql_queries.py` - all CREATE TABLE and SQL statements
- `requirements.txt` - Python dependencies

## Troubleshooting

- If DB init fails, check environment variables and MySQL connectivity.
- Enable more logging by configuring Python logging in `database.py` and other modules.

