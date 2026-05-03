import os
import base64
import hashlib
import hmac
import datetime
import logging
import time
from typing import Optional, Tuple, Any

try:
    import mysql.connector
    from mysql.connector import errorcode
except ImportError:
    mysql = None
    errorcode = None

import sql_queries

DEFAULT_ROLE_PERMISSIONS = {
    "admin": {
        "manage_patients": True,
        "manage_tests": True,
        "manage_inventory": True,
        "manage_staff": True,
        "manage_finances": True,
        "manage_attendance": True,
        "manage_payroll": True,
        "manage_leave": True,
        "view_analytics": True,
        "approve_tests": True,
        "approve_payroll": True,
        "approve_leave": True,
        "generate_reports": True,
    },
    "owner": {
        "manage_patients": True,
        "manage_tests": True,
        "manage_inventory": True,
        "manage_staff": True,
        "manage_finances": True,
        "manage_attendance": True,
        "manage_payroll": True,
        "manage_leave": True,
        "view_analytics": True,
        "approve_tests": True,
        "approve_payroll": True,
        "approve_leave": True,
        "generate_reports": True,
    },
    "lab manager": {
        "manage_tests": True,
        "manage_inventory": True,
        "manage_staff": True,
        "approve_tests": True,
        "view_analytics": False,
        "manage_finances": False,
        "manage_payroll": False,
        "manage_leave": False,
    },
    "receptionist": {
        "manage_patients": True,
        "manage_appointments": True,
        "manage_tests": False,
        "manage_inventory": False,
        "manage_staff": False,
        "manage_finances": False,
        "manage_payroll": False,
        "manage_leave": True,
        "view_analytics": False,
    },
    "doctor": {
        "manage_tests": True,
        "review_results": True,
        "manage_patients": False,
        "manage_inventory": False,
        "manage_staff": False,
        "manage_finances": False,
        "manage_payroll": False,
        "manage_leave": True,
        "view_analytics": False,
    },
    "lab technician": {
        "perform_tests": True,
        "manage_inventory": False,
        "manage_staff": False,
        "manage_finances": False,
        "manage_payroll": False,
        "manage_leave": True,
        "view_analytics": False,
    },
    "patient": {
        "view_own_results": True,
        "manage_patients": False,
        "manage_tests": False,
        "manage_inventory": False,
        "manage_staff": False,
        "manage_finances": False,
        "manage_payroll": False,
        "manage_leave": False,
        "view_analytics": False,
    }
}

class DataEncryptor:
    def __init__(self, key: Optional[bytes] = None):
        key_source = key or os.environ.get("ILMS_ENCRYPTION_KEY", "ilms_default_secret_key_32")
        if isinstance(key_source, str):
            key_source = key_source.encode('utf-8')
        self.key = hashlib.sha256(key_source).digest()

    def _transform(self, data: bytes) -> bytes:
        return bytes(data[i] ^ self.key[i % len(self.key)] for i in range(len(data)))

    def encrypt(self, plaintext: Optional[str]) -> Optional[str]:
        if plaintext is None:
            return None
        raw = plaintext.encode('utf-8')
        encrypted = self._transform(raw)
        return base64.b64encode(encrypted).decode('utf-8')

    def decrypt(self, ciphertext: Optional[str]) -> Optional[str]:
        if ciphertext is None:
            return None
        try:
            raw = base64.b64decode(ciphertext.encode('utf-8'))
            decrypted = self._transform(raw)
            return decrypted.decode('utf-8')
        except Exception:
            return None

def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    if salt is None:
        salt = base64.b64encode(os.urandom(16)).decode('utf-8')
    digest = hashlib.sha256((salt + password).encode('utf-8')).digest()
    return salt, base64.b64encode(digest).decode('utf-8')

def verify_password(password: str, salt: str, stored_hash: str) -> bool:
    digest = hashlib.sha256((salt + password).encode('utf-8')).digest()
    return hmac.compare_digest(base64.b64encode(digest).decode('utf-8'), stored_hash)

class DatabaseManager:
    def __init__(self):
        # Require environment variables for security
        self.host = os.environ.get("ILMS_DB_HOST", "193.203.166.222")
        self.port = int(os.environ.get("ILMS_DB_PORT", "3306"))
        self.database = os.environ.get("ILMS_DB_NAME", "u176582439_ilms")
        self.username = os.environ.get("ILMS_DB_USER", "u176582439_ilms")
        self.password = os.environ.get("ILMS_DB_PASSWORD", "Ashmal...S/*-1")
        
        self.encryptor = DataEncryptor()
        self.connection = None
        self.logger = logging.getLogger(__name__)
        self._initialize_database()

    def _connect(self, use_database: bool = True):
        if mysql is None:
            raise RuntimeError("mysql-connector-python is not installed. Please install it.")
        kwargs = {
            "host": self.host,
            "user": self.username,
            "password": self.password,
            "port": self.port,
            "connection_timeout": 30,  # Increased timeout for remote connections
            "autocommit": False,
        }
        if use_database:
            kwargs["database"] = self.database
        return mysql.connector.connect(**kwargs)

    def _initialize_database(self):
        try:
            conn = self._connect(use_database=False)
            cursor = conn.cursor()
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{self.database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
            )
            cursor.close()
            conn.close()
            self.connection = self._connect(use_database=True)
            self._create_tables()
        except Exception as e:
            self.logger.error(f"DB initialization failed: {e}")
            # Do not set connection to None to allow retries

    def _create_tables(self):
        """Create all tables using queries from sql_queries module"""
        if self.connection is None:
            return
        cursor = self.connection.cursor()
        
        # Execute all CREATE TABLE statements with error handling
        for create_table_sql in sql_queries.ALL_CREATE_TABLES:
            try:
                cursor.execute(create_table_sql)
            except Exception as e:
                self.logger.error(f"Error creating table: {e}")
                # Continue with other tables
        
        self.connection.commit()
        cursor.close()
        self._ensure_roles()
        self._ensure_role_permissions()
        self._ensure_user_password_columns()
        self._seed_default_data()

    def _ensure_roles(self):
        if self.connection is None:
            return
        try:
            cursor = self.connection.cursor()
            roles = ["Admin", "Owner", "Lab Manager", "Receptionist", "Doctor", "Lab Technician", "Patient"]
            for role in roles:
                cursor.execute(sql_queries.INSERT_ROLE, (role,))
            self.connection.commit()
            cursor.close()
        except Exception as e:
            self.logger.error(f"Error ensuring roles: {e}")

    def _ensure_role_permissions(self):
        if self.connection is None:
            return
        try:
            cursor = self.connection.cursor()
            if not self.execute(sql_queries.SELECT_ALL_ROLE_PERMISSIONS):
                for role_name, permissions in DEFAULT_ROLE_PERMISSIONS.items():
                    for permission, allowed in permissions.items():
                        cursor.execute(sql_queries.INSERT_ROLE_PERMISSION, (role_name, permission, int(bool(allowed))))
                self.connection.commit()
            cursor.close()
        except Exception as e:
            self.logger.error(f"Error ensuring role permissions: {e}")

    def _ensure_user_password_columns(self):
        if self.connection is None:
            return
        try:
            cursor = self.connection.cursor()
            cursor.execute("SHOW COLUMNS FROM users LIKE 'password_hash'")
            has_hash = cursor.fetchone() is not None
            cursor.execute("SHOW COLUMNS FROM users LIKE 'password_salt'")
            has_salt = cursor.fetchone() is not None
            if not has_hash:
                cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
            if not has_salt:
                cursor.execute("ALTER TABLE users ADD COLUMN password_salt TEXT")
            if not has_hash or not has_salt:
                self.connection.commit()
            cursor.close()
        except Exception as e:
            self.logger.error(f"Error checking/adding password columns: {e}")

    def _seed_default_data(self):
        if self.connection is None:
            return
        try:
            # Seed specimen data.
            if not self.execute("SELECT 1 FROM specimens LIMIT 1"):
                specimens = [
                    ("S001", "Blood", "Refrigerate 2-8°C"),
                    ("S002", "Urine", "Room Temperature"),
                    ("S003", "Swab", "Transport medium")
                ]
                for specimen in specimens:
                    self.execute(sql_queries.INSERT_UPDATE_SPECIMEN, specimen, commit=True)

            # Seed test groups.
            if not self.execute("SELECT 1 FROM test_groups LIMIT 1"):
                groups = [
                    ("TG01", "Hematology"),
                    ("TG02", "Chemistry Panel"),
                    ("TG03", "Microbiology")
                ]
                for group in groups:
                    self.execute(sql_queries.INSERT_UPDATE_TEST_GROUP, group, commit=True)

            # Seed tests.
            if not self.execute("SELECT 1 FROM tests LIMIT 1"):
                tests = [
                    ("T001", "Complete Blood Count (CBC)", 500.00, "TG01", "S001", "Pending", None, None, None),
                    ("T002", "Basic Metabolic Panel (BMP)", 750.00, "TG02", "S001", "Pending", None, None, None),
                    ("T003", "Urinalysis (UA)", 300.00, "TG02", "S002", "Pending", None, None, None),
                    ("T004", "Strep Test (Rapid)", 2500.00, "TG03", "S003", "Pending", None, None, None)
                ]
                for test in tests:
                    self.execute(sql_queries.INSERT_UPDATE_TEST, test, commit=True)

            # Seed default users.
            if not self.execute("SELECT 1 FROM users LIMIT 1"):
                default_users = [
                    ("U1001", "Receptionist", "receptionist@ilms.com", "Receptionist", 1),
                    ("U1002", "Doctor", "doctor@ilms.com", "Doctor", 1),
                    ("U1003", "Lab Manager", "labmanager@ilms.com", "Lab Manager", 1),
                    ("U1004", "Lab Technician", "labtech@ilms.com", "Lab Technician", 1),
                    ("U1005", "Owner", "owner@ilms.com", "Owner", 1),
                    ("U1006", "Admin", "admin@ilms.com", "Admin", 1)
                ]
                passwords = {
                    "Receptionist": "123",
                    "Doctor": "123",
                    "Lab Manager": "123",
                    "Lab Technician": "123",
                    "Owner": "123",
                    "Admin": "123"
                }
                for user in default_users:
                    salt, password_hash = hash_password(passwords[user[1]])
                    self.execute(
                        sql_queries.INSERT_UPDATE_USER,
                        (user[0], user[1], user[2], user[3], user[4], password_hash, salt),
                        commit=True
                    )

            # Seed default salaries.
            if not self.execute("SELECT 1 FROM employee_salaries LIMIT 1"):
                salary_map = {
                    "U1001": 40000.0,
                    "U1002": 100000.0,
                    "U1003": 80000.0,
                    "U1004": 50000.0,
                    "U1005": 150000.0,
                    "U1006": 75000.0
                }
                for employee_id, base_salary in salary_map.items():
                    self.execute(sql_queries.INSERT_UPDATE_EMPLOYEE_SALARY, (employee_id, base_salary), commit=True)

            # Seed attendance records for staff.
            if not self.execute("SELECT 1 FROM attendance_records LIMIT 1"):
                today = datetime.date.today()
                for employee_id in ["U1001", "U1002", "U1003", "U1004", "U1005", "U1006"]:
                    for days_back in range(1, 11):
                        attendance_date = today - datetime.timedelta(days=days_back)
                        if attendance_date.weekday() < 5:
                            self.execute(
                                sql_queries.INSERT_UPDATE_ATTENDANCE,
                                (employee_id, attendance_date.isoformat(), "09:00:00", "17:30:00", "Present", 8.0),
                                commit=True
                            )

            # Seed inventory data.
            if not self.execute("SELECT 1 FROM inventory LIMIT 1"):
                inventory_items = [
                    ("Blood Vials", 100),
                    ("Swabs", 200),
                    ("Reagent A", 50)
                ]
                for item in inventory_items:
                    self.execute(sql_queries.INSERT_UPDATE_INVENTORY, item, commit=True)

            # Seed revenue history.
            if not self.execute("SELECT 1 FROM daily_revenue_history LIMIT 1"):
                for days_back in range(7, 0, -1):
                    revenue_date = (datetime.date.today() - datetime.timedelta(days=days_back)).isoformat()
                    revenue_amount = 5000.0 + ((7 - days_back) * 1000.0)
                    self.execute(sql_queries.INSERT_UPDATE_DAILY_REVENUE, (revenue_date, revenue_amount), commit=True)

            # Seed leave types if not present
            if not self.execute("SELECT 1 FROM leave_types LIMIT 1"):
                leave_types = [
                    (1, "Annual", 30, 1),
                    (2, "Sick", 12, 1),
                    (3, "Casual", 12, 0),
                    (4, "Maternity", 90, 1)
                ]
                for lt in leave_types:
                    self.execute("INSERT INTO leave_types (id, type_name, max_days_per_year, requires_approval) VALUES (%s, %s, %s, %s)", lt, commit=True)
        except Exception as e:
            self.logger.error(f"Seeding default data failed: {e}")

    def _ensure_connection(self):
        """Ensure the connection is active, reconnect if necessary with retries"""
        if self.connection is None:
            self.logger.info("No connection, initializing database")
            self._initialize_database()
            return
        
        try:
            # Check if connection is alive
            if not self.connection.is_connected():
                self.logger.warning("Connection not connected, attempting reconnect")
                self.connection.reconnect(attempts=3, delay=1)
            else:
                # Ping to ensure it's responsive
                self.connection.ping(reconnect=True, attempts=1, delay=0)
        except mysql.connector.Error as e:
            self.logger.error(f"Connection check failed: {e}, attempting full reconnect")
            try:
                self.connection.reconnect(attempts=3, delay=1)
            except mysql.connector.Error as reconnect_error:
                self.logger.error(f"Reconnect failed: {reconnect_error}, reinitializing")
                # Full reinitialize instead of setting to None
                self.connection = None
                self._initialize_database()

    def safe_execute(self, query: str, params: Optional[tuple] = None, commit: bool = False, max_retries: int = 3):
        """Execute query with connection health checks and retry logic"""
        for attempt in range(max_retries):
            try:
                self._ensure_connection()
                if self.connection is None:
                    self.logger.error("Failed to establish connection after retries")
                    return []
                
                cursor = self.connection.cursor(dictionary=True)
                cursor.execute(query, params or ())
                if commit:
                    self.connection.commit()
                results = cursor.fetchall() if cursor.description else []
                cursor.close()
                return results
            except Exception as e:
                self.logger.warning(f"Query execution failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    # Force reconnection on next attempt
                    if self.connection:
                        try:
                            self.connection.close()
                        except:
                            pass
                    self.connection = None
                else:
                    self.logger.error(f"Query failed after {max_retries} attempts: {query}")
                    return []
        return []

    def execute(self, query: str, params: Optional[tuple] = None, commit: bool = False):
        """Legacy execute method, now uses safe_execute"""
        return self.safe_execute(query, params, commit)

    def encrypt_value(self, value: Optional[str]) -> Optional[str]:
        return self.encryptor.encrypt(value)

    def decrypt_value(self, value: Optional[str]) -> Optional[str]:
        return self.encryptor.decrypt(value)

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None
