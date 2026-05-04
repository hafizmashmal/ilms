# ILMS — Project Overview

## Purpose & Goals

The Integrated Laboratory Management System (ILMS) is a compact, terminal-oriented application that provides essential lab management workflows for small-to-medium diagnostic labs. Its goals are:

- Provide an auditable record of patients, tests, invoices and staff activities.
- Automate routine tasks (invoice creation, test status updates, basic payroll calculations).
- Keep a simple, extensible codebase that can be adapted to different deployment environments.
- Provide a single-node reference implementation suitable for learning, prototyping, and light production use.

## High-level Architecture

- Presentation: `ilms.py` implements a curses-based console UI (terminal-first). The UI drives commands, menus, and displays.
- Application / Domain: Business logic (invoicing, payroll, leave, attendance, tests) is implemented across `ilms.py` and `database_operations.py`.
- Persistence: `database.py` manages MySQL connections, schema initialization, seeding and resilience. SQL and schema artifacts live in `sql_queries.py`.
- Utilities: Encryption, password hashing and other helpers are in `database.py` to centralize security-related functionality.

Data flow summary:
- UI actions call into domain logic which uses `DatabaseOperations` as a thin CRUD facade.
- `DatabaseManager` performs safe queries, connection health checks and handles initialization/seeding.

## Key Components

- `ilms.py` — Main entrypoint and console UI. Handles user sessions, menus, and orchestrates domain logic.
- `database.py` — `DatabaseManager` with connection handling, schema creation and seeding, simple encryptor and password utilities.
- `database_operations.py` — High-level data access methods (CRUD) that the application code calls.
- `sql_queries.py` — Centralized SQL: CREATE TABLE statements, procedures, triggers, views and seed DML.
- `requirements.txt` — Third-party dependencies (e.g., `mysql-connector-python`, `curses` on Unix).

## Deployment & Runtime Notes

- Relational DB: MySQL 8.x recommended. The code auto-creates and seeds schema on first run when DB credentials are available.
- Terminal UI: `curses` works best on Unix-like terminals; on Windows use WSL or a terminal providing curses support.
- Environment variables control DB connection and encryption key (see `README.md`).

## Extension Points

- Replace the terminal UI with a web or REST frontend by keeping `database_operations.py` as the service layer.
- Swap the raw SQL approach for an ORM (SQLAlchemy) and add Alembic migrations for safer schema evolution.
- Replace the simple SHA-256 password scheme with `argon2` for production security.

## File map (quick)

- `ilms.py` — UI + core flows (patients, tests, invoices, payroll, leave)
- `database.py` — Connection, seeding, utilities
- `database_operations.py` — Domain CRUD methods
- `sql_queries.py` — All SQL schema and extensions
- `test.py` — lightweight test/harness
- `requirements.txt` — dependencies

## Recommended next steps

- Add automated tests (unit + integration) around `DatabaseOperations` and payroll calculation logic.
- Introduce a migration system and decouple seeding from schema migrations.
- Add logging configuration and environment-specific settings (development vs production).

## Contributors & License

This repository currently has no explicit license; add a `LICENSE` file if you intend to share publicly.

