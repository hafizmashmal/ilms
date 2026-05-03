"""
Database Operations Layer
All CRUD operations are abstracted here using the DatabaseManager.
This module handles all data access logic.
"""

from typing import List, Dict, Any, Optional, Tuple
import sql_queries



class DatabaseOperations:
    """Encapsulates all database CRUD operations"""

    # ===== Expense Management =====
    def save_expense(self, expense_date: str, amount: float, description: str) -> None:
        """Save an expense record (assumes expenses table exists)"""
        try:
            self.db.execute(
                "INSERT INTO expenses (expense_date, amount, description) VALUES (%s, %s, %s)",
                (expense_date, amount, description),
                commit=True
            )
        except Exception as e:
            if hasattr(self.db, 'logger'):
                self.db.logger.error(f"Failed to save expense: {e}")
            else:
                print(f"Failed to save expense: {e}")

    def get_all_expenses(self) -> List[Dict[str, Any]]:
        try:
            return self.db.execute("SELECT * FROM expenses")
        except Exception as e:
            if hasattr(self.db, 'logger'):
                self.db.logger.error(f"Failed to fetch expenses: {e}")
            else:
                print(f"Failed to fetch expenses: {e}")
            return []

    def __init__(self, db_manager):
        """Initialize with a DatabaseManager instance"""
        self.db = db_manager

    @property
    def connection(self):
        return getattr(self.db, 'connection', None)

    def execute(self, query: str, params: Optional[tuple] = None, commit: bool = False):
        return self.db.execute(query, params, commit=commit)

    def commit(self) -> None:
        if getattr(self.db, 'connection', None):
            self.db.connection.commit()

    # ===== Role Management =====
    def ensure_roles(self, roles: List[str]) -> None:
        """Insert role names if they don't exist"""
        for role in roles:
            self.db.execute(sql_queries.INSERT_ROLE, (role,), commit=True)

    def get_role_permissions_by_role(self, role_name: str) -> Dict[str, bool]:
        """Retrieve permissions for a specific role"""
        rows = self.db.execute(sql_queries.SELECT_ROLE_PERMISSIONS_BY_ROLE, (role_name,))
        return {row['permission']: bool(row['allowed']) for row in rows}

    def get_all_role_permissions(self) -> List[Dict[str, Any]]:
        """Retrieve all role permissions"""
        return self.db.execute(sql_queries.SELECT_ALL_ROLE_PERMISSIONS)

    # ===== User Management =====
    def save_user(self, user_id: str, name: str, email: str, role: str, active: int = 1,
                  password_hash: Optional[str] = None, password_salt: Optional[str] = None) -> None:
        """Save or update a user"""
        self.db.execute(
            sql_queries.INSERT_UPDATE_USER,
            (user_id, name, email, role, active, password_hash, password_salt),
            commit=True
        )

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Retrieve all users"""
        return self.db.execute(sql_queries.SELECT_ALL_USERS)

    # ===== Patient Management =====
    def save_patient(self, patient_id: str, name: str, email: str) -> None:
        """Save or update a patient"""
        self.db.execute(
            sql_queries.INSERT_UPDATE_PATIENT,
            (patient_id, name, email),
            commit=True
        )

    def get_all_patients(self) -> List[Dict[str, Any]]:
        """Retrieve all patients"""
        return self.db.execute(sql_queries.SELECT_ALL_PATIENTS)

    # ===== Specimen Management =====
    def save_specimen(self, specimen_id: str, specimen_type: str, storage_conditions: str) -> None:
        """Save or update a specimen"""
        self.db.execute(
            sql_queries.INSERT_UPDATE_SPECIMEN,
            (specimen_id, specimen_type, storage_conditions),
            commit=True
        )

    def get_all_specimens(self) -> List[Dict[str, Any]]:
        """Retrieve all specimens"""
        return self.db.execute(sql_queries.SELECT_ALL_SPECIMENS)

    # ===== Test Group Management =====
    def save_test_group(self, group_id: str, group_name: str) -> None:
        """Save or update a test group"""
        self.db.execute(
            sql_queries.INSERT_UPDATE_TEST_GROUP,
            (group_id, group_name),
            commit=True
        )

    def get_all_test_groups(self) -> List[Dict[str, Any]]:
        """Retrieve all test groups"""
        return self.db.execute(sql_queries.SELECT_ALL_TEST_GROUPS)

    # ===== Test Management =====
    def save_test(self, test_id: str, name: str, price: float, test_group_id: str,
                  specimen_id: str, status: str, result: Optional[str] = None,
                  patient_id: Optional[str] = None, technician_id: Optional[str] = None) -> None:
        """Save or update a test"""
        self.db.execute(
            sql_queries.INSERT_UPDATE_TEST,
            (test_id, name, price, test_group_id, specimen_id, status, result, patient_id, technician_id),
            commit=True
        )

    def get_all_tests(self) -> List[Dict[str, Any]]:
        """Retrieve all tests"""
        return self.db.execute(sql_queries.SELECT_ALL_TESTS)

    # ===== Invoice Management =====
    def get_all_invoices(self) -> List[Dict[str, Any]]:
        """Retrieve all invoices"""
        return self.db.execute(sql_queries.SELECT_ALL_INVOICES)

    def get_all_invoice_tests(self) -> List[Dict[str, Any]]:
        """Retrieve all invoice-test associations"""
        return self.db.execute(sql_queries.SELECT_ALL_INVOICE_TESTS)

    def save_invoice(self, invoice_id: str, patient_id: str, patient_name: str,
                     date: Any, total_amount: float, fbr_code: str) -> None:
        """Save or update an invoice"""
        self.db.execute(
            sql_queries.INSERT_INVOICE,
            (invoice_id, patient_id, patient_name, date, total_amount, fbr_code),
            commit=True
        )

    def save_invoice_test(self, invoice_id: str, test_id: str) -> None:
        """Save an invoice-test association"""
        self.db.execute(
            sql_queries.INSERT_INVOICE_TEST,
            (invoice_id, test_id),
            commit=True
        )

    # ===== Inventory Management =====
    def save_inventory_item(self, item_name: str, quantity: int) -> None:
        """Save or update an inventory item"""
        self.db.execute(
            sql_queries.INSERT_UPDATE_INVENTORY,
            (item_name, quantity),
            commit=True
        )

    def get_all_inventory(self) -> List[Dict[str, Any]]:
        """Retrieve all inventory items"""
        return self.db.execute(sql_queries.SELECT_ALL_INVENTORY)

    # ===== Revenue Management =====
    def save_daily_revenue(self, revenue_date: str, revenue: float) -> None:
        """Save or update daily revenue"""
        self.db.execute(
            sql_queries.INSERT_UPDATE_DAILY_REVENUE,
            (revenue_date, revenue),
            commit=True
        )

    def get_all_daily_revenue(self) -> List[Dict[str, Any]]:
        """Retrieve all daily revenue records"""
        return self.db.execute(sql_queries.SELECT_ALL_DAILY_REVENUE)

    # ===== Equipment Logs =====
    def save_equipment_log(self, entry: str, entry_date: str) -> None:
        """Save equipment log entry"""
        if isinstance(entry_date, str):
            entry_date = entry_date.replace('T', ' ')
        elif hasattr(entry_date, 'strftime'):
            entry_date = entry_date.strftime('%Y-%m-%d %H:%M:%S')
        self.db.execute(
            sql_queries.INSERT_EQUIPMENT_LOG,
            (entry, entry_date),
            commit=True
        )

    def get_all_equipment_logs(self) -> List[Dict[str, Any]]:
        """Retrieve all equipment logs"""
        return self.db.execute(sql_queries.SELECT_ALL_EQUIPMENT_LOGS)

    # ===== Compliance Reports =====
    def save_compliance_report(self, report_text: str, created_at: str) -> None:
        """Save compliance report"""
        try:
            self.db.execute(
                sql_queries.INSERT_COMPLIANCE_REPORT,
                (report_text, created_at),
                commit=True
            )
        except Exception as e:
            if hasattr(self.db, 'logger'):
                self.db.logger.error(f"Failed to save compliance report: {e}")
            else:
                print(f"Failed to save compliance report: {e}")

    def get_all_compliance_reports(self) -> List[Dict[str, Any]]:
        """Retrieve all compliance reports"""
        return self.db.execute(sql_queries.SELECT_ALL_COMPLIANCE_REPORTS)

    # ===== Appointments =====
    def save_appointment(self, appointment_datetime: str, patient_name: str, status: str) -> None:
        """Save appointment"""
        if isinstance(appointment_datetime, str):
            appointment_datetime = appointment_datetime.replace('T', ' ')
        elif hasattr(appointment_datetime, 'strftime'):
            appointment_datetime = appointment_datetime.strftime('%Y-%m-%d %H:%M:%S')
        self.db.execute(
            sql_queries.INSERT_APPOINTMENT,
            (appointment_datetime, patient_name, status),
            commit=True
        )

    def get_all_appointments(self) -> List[Dict[str, Any]]:
        """Retrieve all appointments"""
        return self.db.execute(sql_queries.SELECT_ALL_APPOINTMENTS)

    # ===== Leave Management =====
    def get_all_leave_types(self) -> List[Dict[str, Any]]:
        """Retrieve all leave types"""
        return self.db.execute(sql_queries.SELECT_ALL_LEAVE_TYPES)

    def get_all_leave_requests(self) -> List[Dict[str, Any]]:
        """Retrieve all leave requests"""
        return self.db.execute(sql_queries.SELECT_ALL_LEAVE_REQUESTS)

    def get_all_leave_balances(self) -> List[Dict[str, Any]]:
        """Retrieve all leave balances"""
        return self.db.execute(sql_queries.SELECT_ALL_LEAVE_BALANCES)

    def save_leave_request(self, employee_id: str, leave_type_id: int, start_date: str,
                          end_date: str, reason: str) -> None:
        """Save leave request"""
        self.db.execute(
            sql_queries.INSERT_LEAVE_REQUEST,
            (employee_id, leave_type_id, start_date, end_date, reason),
            commit=True
        )

    def update_leave_request_status(self, request_id: int, status: str, approved_by: str) -> None:
        """Update leave request status"""
        self.db.execute(
            sql_queries.UPDATE_LEAVE_REQUEST_STATUS,
            (status, approved_by, request_id),
            commit=True
        )

    # ===== Attendance Management =====
    def get_all_attendance(self) -> List[Dict[str, Any]]:
        """Retrieve all attendance records"""
        return self.db.execute(sql_queries.SELECT_ALL_ATTENDANCE)

    def save_attendance_record(self, employee_id: str, attendance_date: str, check_in: Optional[str],
                              check_out: Optional[str], status: str, worked_hours: float) -> None:
        """Save or update attendance record"""
        self.db.execute(
            sql_queries.INSERT_UPDATE_ATTENDANCE,
            (employee_id, attendance_date, check_in, check_out, status, worked_hours),
            commit=True
        )

    # ===== Payroll Management =====
    def get_all_employee_salaries(self) -> List[Dict[str, Any]]:
        """Retrieve all employee salaries"""
        return self.db.execute(sql_queries.SELECT_ALL_EMPLOYEE_SALARIES)

    def get_all_payroll_records(self) -> List[Dict[str, Any]]:
        """Retrieve all payroll records"""
        return self.db.execute(sql_queries.SELECT_ALL_PAYROLL_RECORDS)

    def save_employee_salary(self, employee_id: str, base_salary: float) -> None:
        """Save or update employee salary"""
        self.db.execute(
            sql_queries.INSERT_UPDATE_EMPLOYEE_SALARY,
            (employee_id, base_salary),
            commit=True
        )

    def save_payroll_record(self, employee_id: str, employee_name: str, period_month: int,
                           period_year: int, base_salary: float, days_worked: int,
                           attendance_bonus: float, house_allowance: float,
                           transport_allowance: float, medical_allowance: float,
                           other_allowances: float, gross_salary: float, income_tax: float,
                           provident_fund: float, professional_tax: float, other_deductions: float,
                           total_deductions: float, net_salary: float, status: str,
                           approved_by: Optional[str], approved_date: Optional[str],
                           calculated_at: str) -> None:
        """Save or update payroll record"""
        if approved_date:
            if isinstance(approved_date, str):
                approved_date = approved_date.replace('T', ' ')
            elif hasattr(approved_date, 'strftime'):
                approved_date = approved_date.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(calculated_at, str):
            calculated_at = calculated_at.replace('T', ' ')
        elif hasattr(calculated_at, 'strftime'):
            calculated_at = calculated_at.strftime('%Y-%m-%d %H:%M:%S')
        self.db.execute(
            sql_queries.INSERT_UPDATE_PAYROLL_RECORD,
            (employee_id, employee_name, period_month, period_year, base_salary, days_worked,
             attendance_bonus, house_allowance, transport_allowance, medical_allowance,
             other_allowances, gross_salary, income_tax, provident_fund, professional_tax,
             other_deductions, total_deductions, net_salary, status, approved_by, approved_date,
             calculated_at),
            commit=True
        )

    # ===== Patient Management - Advanced =====
    def update_patient(self, patient_id: str, name: str, email: str) -> None:
        """Update patient information"""
        self.db.execute(
            sql_queries.INSERT_UPDATE_PATIENT,
            (patient_id, name, email),
            commit=True
        )

    def delete_patient_cascade(self, patient_id: str) -> None:
        """Delete patient and all related data (invoices, tests, reports, etc.)"""
        try:
            # Delete patient reports
            self.db.execute(
                "DELETE FROM patient_reports WHERE patient_id = %s",
                (patient_id,),
                commit=True
            )
            # Delete invoice-test associations for this patient's invoices
            self.db.execute(
                """DELETE FROM invoice_tests WHERE invoice_id IN 
                   (SELECT id FROM invoices WHERE patient_id = %s)""",
                (patient_id,),
                commit=True
            )
            # Delete invoices
            self.db.execute(
                "DELETE FROM invoices WHERE patient_id = %s",
                (patient_id,),
                commit=True
            )
            # Delete tests
            self.db.execute(
                "DELETE FROM tests WHERE patient_id = %s",
                (patient_id,),
                commit=True
            )
            # Delete patient user record
            self.db.execute(
                "DELETE FROM patients WHERE id = %s",
                (patient_id,),
                commit=True
            )
            # Delete user record if exists
            self.db.execute(
                "DELETE FROM users WHERE id = %s",
                (patient_id,),
                commit=True
            )
        except Exception as e:
            if hasattr(self.db, 'logger'):
                self.db.logger.error(f"Failed to delete patient cascade: {e}")
            else:
                print(f"Failed to delete patient cascade: {e}")

    # ===== User Management - Advanced =====
    def update_user(self, user_id: str, name: str, email: str, password_hash: Optional[str] = None, 
                   password_salt: Optional[str] = None) -> None:
        """Update user information"""
        if password_hash and password_salt:
            self.db.execute(
                "UPDATE users SET name = %s, email = %s, password_hash = %s, password_salt = %s WHERE id = %s",
                (name, email, password_hash, password_salt, user_id),
                commit=True
            )
        else:
            self.db.execute(
                "UPDATE users SET name = %s, email = %s WHERE id = %s",
                (name, email, user_id),
                commit=True
            )
