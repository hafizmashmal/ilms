# ILMS Database Documentation

## Overview

This project uses MySQL (mysql-connector-python) with InnoDB engine as the primary relational database. MySQL is chosen for wide availability, mature tooling, and support for transactional integrity, foreign keys, stored procedures, views, and triggers used by the application.

Files to review:
- `sql_queries.py` — all `CREATE TABLE`, views, stored procedures, triggers, constraints and sample DML.
- `database.py` — `DatabaseManager` handles initialization, connection pooling, seeding, and runtime operations.
- `database_operations.py` — higher-level CRUD and domain-specific operations.

## Why MySQL / InnoDB

- Transactional support and durable ACID semantics for critical operations (invoices, payroll)
- Foreign key enforcement via InnoDB to maintain referential integrity
- Mature replication, backup and management tooling
- Stored procedures/triggers support used for automation in the schema

## Core Entities & Schemas (summary)

Note: full SQL definitions live in `sql_queries.py`. Below is a concise mapping and rationale.

- `roles` (role_id PK, role_name): Enumerates roles (Admin, Owner, etc.).
- `role_permissions` (role_name, permission, allowed): Permission matrix; composite PK on (role_name, permission).
- `users` (id PK, name, email, role, active, password_hash, password_salt): People who use the system.
- `patients` (id PK, name, email, registered_at): Patient records.
- `patient_reports` (id PK, patient_id FK -> patients.id, report_text, created_at): Freeform patient reports.
- `specimens` (id PK, specimen_type, storage_conditions): Types of biological specimens.
- `test_groups` (id PK, group_name): Grouping of tests.
- `tests` (id PK, name, price, test_group_id FK, specimen_id FK, status, result, patient_id FK, technician_id FK): Lab tests as primary transactional records.
- `invoices` (id PK, patient_id FK, patient_name, date, total_amount, fbr_code): Billing invoices
- `invoice_tests` (invoice_id FK, test_id FK): Many-to-many link between invoices and tests.
- `attendance_records` (employee_id FK, attendance_date PK composite, check_in, check_out, status, worked_hours)
- `employee_salaries` (employee_id PK, base_salary)
- `payroll_records` (id PK, employee_id FK, period_month, period_year, gross/net, deductions, UNIQUE employee+month+year)
- `leave_types`, `leave_requests`, `employee_leave_balances` — leave management tables
- `inventory` (item_name PK, quantity, created_by FK, last_updated_by FK)
- `appointments`, `equipment_logs`, `compliance_reports`, `daily_revenue_history`, `performance_metrics`, `expenses`.

## Keys, Indexes and Constraints

- Primary keys are defined for uniqueness and fast lookups.
- Foreign keys enforce relationships and cascade behaviors where applicable (ON DELETE SET NULL for user references in non-critical logs).
- Composite unique constraints (e.g., payroll_records unique employee/month/year) prevent duplication.
- CHECK constraints (where supported) guard against invalid values (e.g., non-negative invoice totals).
- Add indexes on frequently queried columns (e.g., tests.patient_id, tests.status, invoices.date) to improve read performance.

## Normalization & Normal Forms

The schema follows normalized design through 3NF:

- 1NF: All tables use atomic columns (no repeating groups).
- 2NF: Non-key attributes depend on the whole primary key (composite PKs are used intentionally where needed, like `role_permissions` and `invoice_tests`).
- 3NF: Non-key attributes are not transitively dependent on the primary key. For example, `patient_name` is stored on invoices for denormalized quick access/history; canonical patient details remain in `patients`.

Denormalization: `invoices.patient_name` is intentionally duplicated to preserve historical invoice data even if the patient record changes.

## Relationships

- One-to-many: `patients` -> `tests`, `patients` -> `invoices`, `test_groups` -> `tests`.
- Many-to-many: `invoices` <-> `tests` via `invoice_tests`.
- One-to-one or optional: `users` -> `employee_salaries` (one salary per employee), `employee_leave_balances` per employee.

## Triggers, Procedures, Views

- `sp_create_invoice`: Computes total from `tests` and inserts invoice and invoice_tests. Useful for idempotent invoice creation.
- `fn_calc_income_tax`: Simple tax calculation function used by payroll.
- `trg_after_invoice_insert`: Marks tests as invoiced after invoice creation.
- `trg_after_test_update`: When a test becomes `Completed`, insert a row into `patient_reports`.
- Views: `patient_test_summary`, `payroll_summary` provide aggregated reporting-ready datasets.

## Sample ERD (textual)

- users (1) - (N) tests (technician_id)
- patients (1) - (N) tests (patient_id)
- tests (N) - (N) invoices via invoice_tests
- test_groups (1) - (N) tests
- specimens (1) - (N) tests

## Backup & Restore

Recommended strategies:
- Regular logical backups: `mysqldump --single-transaction --routines --triggers --events --databases ilms_db > ilms_backup.sql`
- Use binary backups (`mysqlbackup` or Percona XtraBackup) for large datasets.
- Store backups offsite and verify restores periodically.

## Migrations

This project currently relies on inline SQL in `sql_queries.py` and `DatabaseManager` auto-creation. For production use, adopt a migration tool (Alembic is for SQLAlchemy; for raw SQL consider `flyway`, `liquibase`, or a simple custom migration table and scripts) to manage schema evolution safely.

## Security Considerations

- Use a dedicated DB user with only required privileges.
- Do not commit real credentials into source control.
- Use TLS for DB connections when traversing untrusted networks.
- Secure backups and rotation policies for `ILMS_ENCRYPTION_KEY`.
- Hash passwords with a proper slow KDF (the current implementation uses SHA-256 + salt; consider adopting `bcrypt`/`scrypt`/`argon2` for production).

## Performance Hints

- Add appropriate indexes on columns used in WHERE and JOIN clauses (e.g., `tests.patient_id`, `tests.status`, `invoices.date`).
- Monitor slow queries and add composite indexes where necessary.
- Consider pagination for large result sets in UI calls.

## Operational Notes

- The `DatabaseManager` in `database.py` contains robust reconnect and seeding logic; ensure environment variables are set before first run.
- Multi-statement SQL objects (procedures, triggers) should be executed with a connector/client that supports multi-statement execution (the code handles this where possible).

## Example queries

- Create an invoice via procedure: `CALL sp_create_invoice('INV_001','P_SEED_001','Seed Patient','FBR-001')`.
- Get patient test summary: `SELECT * FROM patient_test_summary`.
- Get pending tests: `SELECT * FROM tests WHERE status = 'Pending'`.

## Further improvements

- Migrate to a migration-managed schema for safer updates.
- Replace custom password hashing with `argon2` and integrate MFA for sensitive roles.
- Add RBAC enforcement at both application and DB level where appropriate.

