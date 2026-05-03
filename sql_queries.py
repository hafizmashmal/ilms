# Expense Table
CREATE_EXPENSES_TABLE = """
CREATE TABLE IF NOT EXISTS expenses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    expense_date DATE NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    description VARCHAR(255) NOT NULL,
    created_by VARCHAR(50) DEFAULT NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB
"""
"""
SQL Query Definitions for ILMS
All SQL statements and query templates are centralized here.
"""

# CREATE TABLE Statements
CREATE_ROLES_TABLE = """
CREATE TABLE IF NOT EXISTS roles (
    role_id INT AUTO_INCREMENT PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL
) ENGINE=InnoDB
"""

CREATE_ROLE_PERMISSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS role_permissions (
    role_name VARCHAR(50) NOT NULL,
    permission VARCHAR(100) NOT NULL,
    allowed TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (role_name, permission)
) ENGINE=InnoDB
"""

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    active TINYINT(1) NOT NULL DEFAULT 1,
    password_hash TEXT,
    password_salt TEXT
) ENGINE=InnoDB
"""

CREATE_PATIENTS_TABLE = """
CREATE TABLE IF NOT EXISTS patients (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    registered_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB
"""

CREATE_PATIENT_REPORTS_TABLE = """
CREATE TABLE IF NOT EXISTS patient_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL,
    report_text TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
) ENGINE=InnoDB
"""

CREATE_SPECIMENS_TABLE = """
CREATE TABLE IF NOT EXISTS specimens (
    id VARCHAR(50) PRIMARY KEY,
    specimen_type VARCHAR(100) NOT NULL,
    storage_conditions VARCHAR(255) NOT NULL
) ENGINE=InnoDB
"""

CREATE_TEST_GROUPS_TABLE = """
CREATE TABLE IF NOT EXISTS test_groups (
    id VARCHAR(50) PRIMARY KEY,
    group_name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB
"""

CREATE_TESTS_TABLE = """
CREATE TABLE IF NOT EXISTS tests (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(12,2) NOT NULL,
    test_group_id VARCHAR(50) NOT NULL,
    specimen_id VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    result TEXT,
    patient_id VARCHAR(50),
    technician_id VARCHAR(50),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (test_group_id) REFERENCES test_groups(id),
    FOREIGN KEY (specimen_id) REFERENCES specimens(id),
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (technician_id) REFERENCES users(id)
) ENGINE=InnoDB
"""

CREATE_INVOICES_TABLE = """
CREATE TABLE IF NOT EXISTS invoices (
    id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL,
    patient_name VARCHAR(100) NOT NULL,
    date DATETIME NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    fbr_code VARCHAR(100) NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
) ENGINE=InnoDB
"""

CREATE_INVOICE_TESTS_TABLE = """
CREATE TABLE IF NOT EXISTS invoice_tests (
    invoice_id VARCHAR(50) NOT NULL,
    test_id VARCHAR(50) NOT NULL,
    PRIMARY KEY (invoice_id, test_id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(id),
    FOREIGN KEY (test_id) REFERENCES tests(id)
) ENGINE=InnoDB
"""

CREATE_ATTENDANCE_RECORDS_TABLE = """
CREATE TABLE IF NOT EXISTS attendance_records (
    employee_id VARCHAR(50) NOT NULL,
    attendance_date DATE NOT NULL,
    check_in TIME,
    check_out TIME,
    status VARCHAR(50) NOT NULL,
    worked_hours DECIMAL(5,2) NOT NULL,
    PRIMARY KEY (employee_id, attendance_date),
    FOREIGN KEY (employee_id) REFERENCES users(id)
) ENGINE=InnoDB
"""

CREATE_EMPLOYEE_SALARIES_TABLE = """
CREATE TABLE IF NOT EXISTS employee_salaries (
    employee_id VARCHAR(50) PRIMARY KEY,
    base_salary DECIMAL(12,2) NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES users(id)
) ENGINE=InnoDB
"""

CREATE_PAYROLL_RECORDS_TABLE = """
CREATE TABLE IF NOT EXISTS payroll_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id VARCHAR(50) NOT NULL,
    employee_name VARCHAR(255) NOT NULL,
    period_month INT NOT NULL,
    period_year INT NOT NULL,
    base_salary DECIMAL(12,2) NOT NULL,
    days_worked INT NOT NULL,
    attendance_bonus DECIMAL(12,2) NOT NULL,
    house_allowance DECIMAL(12,2) NOT NULL,
    transport_allowance DECIMAL(12,2) NOT NULL,
    medical_allowance DECIMAL(12,2) NOT NULL,
    other_allowances DECIMAL(12,2) NOT NULL,
    gross_salary DECIMAL(12,2) NOT NULL,
    income_tax DECIMAL(12,2) NOT NULL,
    provident_fund DECIMAL(12,2) NOT NULL,
    professional_tax DECIMAL(12,2) NOT NULL,
    other_deductions DECIMAL(12,2) NOT NULL,
    total_deductions DECIMAL(12,2) NOT NULL,
    net_salary DECIMAL(12,2) NOT NULL,
    status VARCHAR(50) NOT NULL,
    approved_by VARCHAR(50),
    approved_date DATETIME,
    calculated_at DATETIME NOT NULL,
    UNIQUE KEY uniq_employee_period (employee_id, period_month, period_year),
    FOREIGN KEY (employee_id) REFERENCES users(id),
    FOREIGN KEY (approved_by) REFERENCES users(id)
) ENGINE=InnoDB
"""

CREATE_LEAVE_TYPES_TABLE = """
CREATE TABLE IF NOT EXISTS leave_types (
    id INT PRIMARY KEY,
    type_name VARCHAR(100) NOT NULL,
    max_days_per_year INT NOT NULL,
    requires_approval TINYINT(1) NOT NULL
) ENGINE=InnoDB
"""

CREATE_LEAVE_REQUESTS_TABLE = """
CREATE TABLE IF NOT EXISTS leave_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id VARCHAR(50) NOT NULL,
    leave_type_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    reason VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Requested',
    approved_by VARCHAR(50),
    requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME
) ENGINE=InnoDB
"""

CREATE_EMPLOYEE_LEAVE_BALANCES_TABLE = """
CREATE TABLE IF NOT EXISTS employee_leave_balances (
    employee_id VARCHAR(50) PRIMARY KEY,
    annual_leave INT NOT NULL,
    sick_leave INT NOT NULL,
    casual_leave INT NOT NULL,
    maternity_leave INT NOT NULL,
    used_annual INT NOT NULL,
    used_sick INT NOT NULL,
    used_casual INT NOT NULL,
    used_maternity INT NOT NULL
) ENGINE=InnoDB
"""

CREATE_INVENTORY_TABLE = """
CREATE TABLE IF NOT EXISTS inventory (
    item_name VARCHAR(100) PRIMARY KEY,
    quantity INT NOT NULL,
    created_by VARCHAR(50) DEFAULT NULL,
    last_updated_by VARCHAR(50) DEFAULT NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (last_updated_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB
"""

CREATE_APPOINTMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS appointments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    appointment_datetime DATETIME NOT NULL,
    patient_name VARCHAR(255) NOT NULL,
    created_by VARCHAR(50) DEFAULT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Scheduled',
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB
"""

CREATE_EQUIPMENT_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS equipment_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    entry TEXT NOT NULL,
    entry_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50) DEFAULT NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB
"""

CREATE_COMPLIANCE_REPORTS_TABLE = """
CREATE TABLE IF NOT EXISTS compliance_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_text TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50) DEFAULT NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB
"""

CREATE_DAILY_REVENUE_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS daily_revenue_history (
    revenue_date DATE PRIMARY KEY,
    revenue DECIMAL(12,2) NOT NULL,
    recorded_by VARCHAR(50) DEFAULT NULL,
    FOREIGN KEY (recorded_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB
"""

CREATE_PERFORMANCE_METRICS_TABLE = """
CREATE TABLE IF NOT EXISTS performance_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(12,2) NOT NULL,
    metric_date DATE NOT NULL,
    employee_id VARCHAR(50) DEFAULT NULL,
    FOREIGN KEY (employee_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB
"""

# List of all CREATE TABLE statements (for initialization)
ALL_CREATE_TABLES = [
    CREATE_EXPENSES_TABLE,
    CREATE_ROLES_TABLE,
    CREATE_ROLE_PERMISSIONS_TABLE,
    CREATE_USERS_TABLE,
    CREATE_PATIENTS_TABLE,
    CREATE_PATIENT_REPORTS_TABLE,
    CREATE_SPECIMENS_TABLE,
    CREATE_TEST_GROUPS_TABLE,
    CREATE_TESTS_TABLE,
    CREATE_INVOICES_TABLE,
    CREATE_INVOICE_TESTS_TABLE,
    CREATE_ATTENDANCE_RECORDS_TABLE,
    CREATE_EMPLOYEE_SALARIES_TABLE,
    CREATE_PAYROLL_RECORDS_TABLE,
    CREATE_LEAVE_TYPES_TABLE,
    CREATE_LEAVE_REQUESTS_TABLE,
    CREATE_EMPLOYEE_LEAVE_BALANCES_TABLE,
    CREATE_INVENTORY_TABLE,
    CREATE_APPOINTMENTS_TABLE,
    CREATE_EQUIPMENT_LOGS_TABLE,
    CREATE_COMPLIANCE_REPORTS_TABLE,
    CREATE_DAILY_REVENUE_HISTORY_TABLE,
    CREATE_PERFORMANCE_METRICS_TABLE,
]

# Query Templates (INSERT, UPDATE, SELECT)

# Role Management
INSERT_ROLE = "INSERT IGNORE INTO roles (role_name) VALUES (%s)"

INSERT_ROLE_PERMISSION = """
INSERT INTO role_permissions (role_name, permission, allowed)
VALUES (%s, %s, %s)
ON DUPLICATE KEY UPDATE
    allowed = VALUES(allowed)
"""

SELECT_ROLE_PERMISSIONS_BY_ROLE = "SELECT * FROM role_permissions WHERE role_name = %s"
SELECT_ALL_ROLE_PERMISSIONS = "SELECT * FROM role_permissions"

# User Management
INSERT_UPDATE_USER = """
INSERT INTO users (id, name, email, role, active, password_hash, password_salt)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    email = VALUES(email),
    role = VALUES(role),
    active = VALUES(active),
    password_hash = VALUES(password_hash),
    password_salt = VALUES(password_salt)
"""

SELECT_ALL_USERS = "SELECT * FROM users"

# Patient Management
INSERT_UPDATE_PATIENT = """
INSERT INTO patients (id, name, email)
VALUES (%s, %s, %s)
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    email = VALUES(email)
"""

SELECT_ALL_PATIENTS = "SELECT * FROM patients"

# Specimen Management
INSERT_UPDATE_SPECIMEN = """
INSERT INTO specimens (id, specimen_type, storage_conditions)
VALUES (%s, %s, %s)
ON DUPLICATE KEY UPDATE
    specimen_type = VALUES(specimen_type),
    storage_conditions = VALUES(storage_conditions)
"""

SELECT_ALL_SPECIMENS = "SELECT * FROM specimens"

# Test Group Management
INSERT_UPDATE_TEST_GROUP = """
INSERT INTO test_groups (id, group_name)
VALUES (%s, %s)
ON DUPLICATE KEY UPDATE
    group_name = VALUES(group_name)
"""

SELECT_ALL_TEST_GROUPS = "SELECT * FROM test_groups"

# Test Management
INSERT_UPDATE_TEST = """
INSERT INTO tests (id, name, price, test_group_id, specimen_id, status, result, patient_id, technician_id)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    price = VALUES(price),
    test_group_id = VALUES(test_group_id),
    specimen_id = VALUES(specimen_id),
    status = VALUES(status),
    result = VALUES(result),
    patient_id = VALUES(patient_id),
    technician_id = VALUES(technician_id)
"""

SELECT_ALL_TESTS = "SELECT * FROM tests"

# Invoice Management
SELECT_ALL_INVOICES = "SELECT * FROM invoices"
SELECT_ALL_INVOICE_TESTS = "SELECT * FROM invoice_tests"

INSERT_INVOICE = """
INSERT INTO invoices (id, patient_id, patient_name, date, total_amount, fbr_code)
VALUES (%s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    patient_id = VALUES(patient_id),
    patient_name = VALUES(patient_name),
    date = VALUES(date),
    total_amount = VALUES(total_amount),
    fbr_code = VALUES(fbr_code)
"""

INSERT_INVOICE_TEST = "INSERT IGNORE INTO invoice_tests (invoice_id, test_id) VALUES (%s, %s)"

# Inventory Management
INSERT_UPDATE_INVENTORY = """
INSERT INTO inventory (item_name, quantity)
VALUES (%s, %s)
ON DUPLICATE KEY UPDATE
    quantity = VALUES(quantity)
"""

SELECT_ALL_INVENTORY = "SELECT * FROM inventory"

# Revenue History Management
INSERT_UPDATE_DAILY_REVENUE = """
INSERT INTO daily_revenue_history (revenue_date, revenue)
VALUES (%s, %s)
ON DUPLICATE KEY UPDATE
    revenue = VALUES(revenue)
"""

SELECT_ALL_DAILY_REVENUE = "SELECT * FROM daily_revenue_history"

# Equipment Logs
INSERT_EQUIPMENT_LOG = "INSERT INTO equipment_logs (entry, entry_date) VALUES (%s, %s)"
SELECT_ALL_EQUIPMENT_LOGS = "SELECT * FROM equipment_logs"

# Compliance Reports
INSERT_COMPLIANCE_REPORT = "INSERT INTO compliance_reports (report_text, created_at) VALUES (%s, %s)"
SELECT_ALL_COMPLIANCE_REPORTS = "SELECT * FROM compliance_reports"

# Appointments
INSERT_APPOINTMENT = "INSERT INTO appointments (appointment_datetime, patient_name, status) VALUES (%s, %s, %s)"
SELECT_ALL_APPOINTMENTS = "SELECT * FROM appointments"

# Leave Management
SELECT_ALL_LEAVE_TYPES = "SELECT * FROM leave_types"
SELECT_ALL_LEAVE_REQUESTS = "SELECT * FROM leave_requests"
SELECT_ALL_LEAVE_BALANCES = "SELECT * FROM employee_leave_balances"

INSERT_LEAVE_REQUEST = """
INSERT INTO leave_requests (employee_id, leave_type_id, start_date, end_date, reason)
VALUES (%s, %s, %s, %s, %s)
"""

UPDATE_LEAVE_REQUEST_STATUS = """
UPDATE leave_requests
SET status = %s, approved_by = %s, reviewed_at = NOW()
WHERE id = %s
"""

# Attendance Management
SELECT_ALL_ATTENDANCE = "SELECT * FROM attendance_records"

INSERT_UPDATE_ATTENDANCE = """
INSERT INTO attendance_records (employee_id, attendance_date, check_in, check_out, status, worked_hours)
VALUES (%s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    check_in = VALUES(check_in),
    check_out = VALUES(check_out),
    status = VALUES(status),
    worked_hours = VALUES(worked_hours)
"""

# Payroll Management
SELECT_ALL_EMPLOYEE_SALARIES = "SELECT * FROM employee_salaries"
SELECT_ALL_PAYROLL_RECORDS = "SELECT * FROM payroll_records"

INSERT_UPDATE_EMPLOYEE_SALARY = """
INSERT INTO employee_salaries (employee_id, base_salary)
VALUES (%s, %s)
ON DUPLICATE KEY UPDATE
    base_salary = VALUES(base_salary)
"""

INSERT_UPDATE_PAYROLL_RECORD = """
INSERT INTO payroll_records (
    employee_id, employee_name, period_month, period_year, base_salary,
    days_worked, attendance_bonus, house_allowance, transport_allowance, medical_allowance,
    other_allowances, gross_salary, income_tax, provident_fund, professional_tax,
    other_deductions, total_deductions, net_salary, status, approved_by, approved_date, calculated_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
ON DUPLICATE KEY UPDATE
    base_salary = VALUES(base_salary),
    days_worked = VALUES(days_worked),
    attendance_bonus = VALUES(attendance_bonus),
    house_allowance = VALUES(house_allowance),
    transport_allowance = VALUES(transport_allowance),
    medical_allowance = VALUES(medical_allowance),
    other_allowances = VALUES(other_allowances),
    gross_salary = VALUES(gross_salary),
    income_tax = VALUES(income_tax),
    provident_fund = VALUES(provident_fund),
    professional_tax = VALUES(professional_tax),
    other_deductions = VALUES(other_deductions),
    total_deductions = VALUES(total_deductions),
    net_salary = VALUES(net_salary),
    status = VALUES(status),
    approved_by = VALUES(approved_by),
    approved_date = VALUES(approved_date),
    calculated_at = VALUES(calculated_at)
"""

# Patient Reports
INSERT_PATIENT_REPORT = """
INSERT INTO patient_reports (patient_id, report_text)
VALUES (%s, %s)
"""

SELECT_ALL_PATIENT_REPORTS = "SELECT * FROM patient_reports"

SELECT_PATIENT_REPORTS_BY_PATIENT = "SELECT * FROM patient_reports WHERE patient_id = %s"
