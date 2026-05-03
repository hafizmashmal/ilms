import curses
import time
import datetime
import os
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Type

from database import DatabaseManager, hash_password, verify_password
from database_operations import DatabaseOperations

ROLE_PERMISSIONS_CACHE: Dict[str, Dict[str, bool]] = {}

class Specimen:
    def __init__(self, id: str, type: str, storage_conditions: str):
        self.id = id
        self.type = type
        self.storage_conditions = storage_conditions

class Test:
    def __init__(self, id: str, name: str, price: float, test_group_name: str, specimen: Specimen):
        self.id = id
        self.name = name
        self.price = price
        self.test_group_name = test_group_name
        self.specimen = specimen
        self.status: str = "Pending"
        self.result: Optional[str] = None
        self.patient_id: Optional[str] = None
        self.technician_id: Optional[str] = None

class TestGroup:
    def __init__(self, id: str, group_name: str):
        self.id = id
        self.group_name = group_name
        self.tests: List[Test] = []

    def add_test(self, test: Test):
        if test not in self.tests:
            self.tests.append(test)

class Invoice:
    def __init__(self, id: str, patient_id: str, patient_name: str, tests: List[Test]):
        self.id = id
        self.patient_id = patient_id     
        self.patient_name = patient_name 
        self.tests = tests
        self.date = datetime.datetime.now()
        self.total_amount = sum(test.price for test in self.tests)
        self.fbr_code = f"FBR-{int(time.time())}-{patient_id}"

    def get_display_format(self) -> str:
        lines = [
            f"Invoice ID: {self.id}",
            f"Patient: {self.patient_name} (ID: {self.patient_id})",
            f"Date: {self.date.strftime('%Y-%m-%d %H:%M')}",
            "─" * 40, "ITEMIZED TESTS"
        ]
        for test in self.tests:
            price_str = f"Rs.{test.price:,.2f}"
            lines.append(f"- {test.name.ljust(25)} {price_str.rjust(10)}")
        lines.append("─" * 40)
        total_str = f"Rs.{self.total_amount:,.2f}"
        lines.append(f"TOTAL AMOUNT: {total_str.rjust(26)}")
        lines.append(f"\nFBR Code: {self.fbr_code}")
        return "\n".join(lines)


class LeaveType:
    def __init__(self, id: int, type_name: str, max_days_per_year: int, requires_approval: bool):
        self.id = id
        self.type_name = type_name
        self.max_days_per_year = max_days_per_year
        self.requires_approval = requires_approval

class LeaveRequest:
    def __init__(self, id: int, employee_id: str, leave_type_id: int, start_date: datetime.date, 
                 end_date: datetime.date, reason: str, status: str = "Requested", 
                 approved_by: Optional[str] = None, requested_at: Optional[datetime.datetime] = None,
                 reviewed_at: Optional[datetime.datetime] = None):
        self.id = id
        self.employee_id = employee_id
        self.leave_type_id = leave_type_id
        self.start_date = start_date
        self.end_date = end_date
        self.reason = reason
        self.status = status
        self.approved_by = approved_by
        self.requested_at = requested_at or datetime.datetime.now()
        self.reviewed_at = reviewed_at

class LeaveBalance:
    def __init__(self, employee_id: str, annual_leave: int = 30, sick_leave: int = 12, 
                 casual_leave: int = 12, maternity_leave: int = 90, used_annual: int = 0,
                 used_sick: int = 0, used_casual: int = 0, used_maternity: int = 0):
        self.employee_id = employee_id
        self.annual_leave = annual_leave
        self.sick_leave = sick_leave
        self.casual_leave = casual_leave
        self.maternity_leave = maternity_leave
        self.used_annual = used_annual
        self.used_sick = used_sick
        self.used_casual = used_casual
        self.used_maternity = used_maternity

    def get_remaining_days(self, leave_type: str) -> int:
        if leave_type == "Annual":
            return self.annual_leave - self.used_annual
        elif leave_type == "Sick":
            return self.sick_leave - self.used_sick
        elif leave_type == "Casual":
            return self.casual_leave - self.used_casual
        elif leave_type == "Maternity":
            return self.maternity_leave - self.used_maternity
        return 0


class AttendanceRecord:
    def __init__(self, employee_id: str, date: datetime.date, check_in: Optional[datetime.time] = None, 
                 check_out: Optional[datetime.time] = None, status: str = "Absent"):
        self.employee_id = employee_id
        self.date = date
        self.check_in = check_in
        self.check_out = check_out
        self.status = status  # "Present", "Absent", "Leave", "Half-day"
        self.worked_hours = self._calculate_worked_hours()

    def _calculate_worked_hours(self) -> float:
        if self.check_in and self.check_out and self.status == "Present":
            dt_checkin = datetime.datetime.combine(self.date, self.check_in)
            dt_checkout = datetime.datetime.combine(self.date, self.check_out)
            delta = dt_checkout - dt_checkin
            return delta.total_seconds() / 3600
        elif self.status == "Half-day":
            return 4.0
        return 0.0

    def to_dict(self):
        return {
            "employee_id": self.employee_id,
            "date": self.date.isoformat(),
            "check_in": self.check_in.isoformat() if self.check_in else None,
            "check_out": self.check_out.isoformat() if self.check_out else None,
            "status": self.status,
            "worked_hours": self.worked_hours
        }


class LeaveManager:
    def __init__(self, db_operations: DatabaseOperations):
        self.db_operations = db_operations
        self.leave_types: Dict[int, LeaveType] = {}
        self.leave_requests: List[LeaveRequest] = []
        self.leave_balances: Dict[str, LeaveBalance] = {}
        self._load_from_db()

    def _load_from_db(self):
        if self.db_operations.connection is None:
            return

        def _to_date(value):
            if isinstance(value, datetime.date):
                return value
            if isinstance(value, str):
                return datetime.date.fromisoformat(value)
            return None

        def _to_datetime(value):
            if isinstance(value, datetime.datetime):
                return value
            if isinstance(value, str):
                return datetime.datetime.fromisoformat(value)
            return None

        self.leave_types.clear()
        for row in self.db_operations.get_all_leave_types():
            leave_type = LeaveType(
                id=int(row["id"]),
                type_name=row["type_name"],
                max_days_per_year=int(row["max_days_per_year"]),
                requires_approval=bool(row["requires_approval"])
            )
            self.leave_types[leave_type.id] = leave_type

        self.leave_requests.clear()
        for row in self.db_operations.get_all_leave_requests():
            request = LeaveRequest(
                id=int(row["id"]),
                employee_id=row["employee_id"],
                leave_type_id=int(row["leave_type_id"]),
                start_date=_to_date(row["start_date"]),
                end_date=_to_date(row["end_date"]),
                reason=row["reason"],
                status=row["status"],
                approved_by=row.get("approved_by"),
                requested_at=_to_datetime(row.get("requested_at")),
                reviewed_at=_to_datetime(row.get("reviewed_at"))
            )
            self.leave_requests.append(request)

        self.leave_balances.clear()
        for row in self.db_operations.get_all_leave_balances():
            balance = LeaveBalance(
                employee_id=row["employee_id"],
                annual_leave=int(row["annual_leave"]),
                sick_leave=int(row["sick_leave"]),
                casual_leave=int(row["casual_leave"]),
                maternity_leave=int(row["maternity_leave"]),
                used_annual=int(row["used_annual"]),
                used_sick=int(row["used_sick"]),
                used_casual=int(row["used_casual"]),
                used_maternity=int(row["used_maternity"])
            )
            self.leave_balances[balance.employee_id] = balance

    def request_leave(self, request: LeaveRequest) -> bool:
        """Submit a leave request"""
        try:
            if self.db_operations.connection:
                self.db_operations.save_leave_request(
                    request.employee_id,
                    request.leave_type_id,
                    request.start_date.isoformat(),
                    request.end_date.isoformat(),
                    request.reason
                )
            self._load_from_db()
            return True
        except Exception:
            return False

    def approve_leave(self, request_id: int, approved_by: str):
        if self.db_operations.connection:
            self.db_operations.update_leave_request_status(
                request_id, 'Approved', approved_by
            )
        self._load_from_db()

    def reject_leave(self, request_id: int, approved_by: str):
        if self.db_operations.connection:
            self.db_operations.update_leave_request_status(
                request_id, 'Rejected', approved_by
            )
        self._load_from_db()

    def get_leave_types(self) -> Dict[int, LeaveType]:
        return self.leave_types

    def get_pending_requests(self) -> List[LeaveRequest]:
        return [r for r in self.leave_requests if r.status == "Pending"]

    def get_leave_balance(self, employee_id: str) -> Optional[LeaveBalance]:
        return self.leave_balances.get(employee_id)


class Attendance:
    def __init__(self, db_operations: DatabaseOperations):
        self.db_operations = db_operations
        self.records: List[AttendanceRecord] = []
        self._load_from_db()

    def _load_from_db(self):
        if self.db_operations.connection:
            results = self.db_operations.get_all_attendance()
            self.records.clear()
            if results:
                for row in results:
                    # Convert TIME columns from timedelta to datetime.time
                    def timedelta_to_time(td):
                        if td is None:
                            return None
                        hours, remainder = divmod(td.seconds, 3600)
                        minutes, seconds = divmod(remainder, 60)
                        return datetime.time(hours, minutes, seconds)
                    
                    record = AttendanceRecord(
                        employee_id=row["employee_id"],
                        date=row["attendance_date"] if isinstance(row["attendance_date"], datetime.date) else datetime.date.fromisoformat(row["attendance_date"]),
                        check_in=timedelta_to_time(row["check_in"]),
                        check_out=timedelta_to_time(row["check_out"]),
                        status=row["status"]
                    )
                    record.worked_hours = float(row.get("worked_hours", 0.0))
                    self.records.append(record)

    def add_record(self, record: AttendanceRecord):
        # Remove if already exists for same employee and date
        self.records = [r for r in self.records if not (r.employee_id == record.employee_id and r.date == record.date)]
        self.records.append(record)
        # Save to DB
        if self.db_operations.connection:
            self.db_operations.save_attendance_record(
                record.employee_id,
                record.date,
                record.check_in,
                record.check_out,
                record.status,
                record.worked_hours
            )

    def get_employee_attendance(self, employee_id: str, month: Optional[int] = None, year: Optional[int] = None) -> List[AttendanceRecord]:
        records = [r for r in self.records if r.employee_id == employee_id]
        if month and year:
            records = [r for r in records if r.date.month == month and r.date.year == year]
        return sorted(records, key=lambda r: r.date)

    def get_attendance_summary(self, employee_id: str, month: Optional[int] = None, year: Optional[int] = None) -> Dict[str, Any]:
        records = self.get_employee_attendance(employee_id, month, year)
        return {
            "total_present": len([r for r in records if r.status == "Present"]),
            "total_absent": len([r for r in records if r.status == "Absent"]),
            "total_leave": len([r for r in records if r.status == "Leave"]),
            "total_half_day": len([r for r in records if r.status == "Half-day"]),
            "total_worked_hours": sum(r.worked_hours for r in records),
            "average_hours_per_day": sum(r.worked_hours for r in records) / len([r for r in records if r.worked_hours > 0]) if any(r.worked_hours > 0 for r in records) else 0
        }


class PayrollRecord:
    def __init__(self, employee_id: str, employee_name: str, month: int, year: int, 
                 base_salary: float = 0.0, days_worked: int = 0):
        self.employee_id = employee_id
        self.employee_name = employee_name
        self.month = month
        self.year = year
        self.base_salary = base_salary
        self.days_worked = days_worked
        self.attendance_bonus = 0.0
        self.house_allowance = 0.0
        self.transport_allowance = 0.0
        self.medical_allowance = 0.0
        self.other_allowances = 0.0
        self.gross_salary = 0.0
        self.income_tax = 0.0
        self.provident_fund = 0.0
        self.professional_tax = 0.0
        self.other_deductions = 0.0
        self.total_deductions = 0.0
        self.net_salary = 0.0
        self.status = "Draft"  # Draft, Approved, Paid
        self.approved_by = None
        self.approved_date = None
        self.calculated_date = datetime.datetime.now()

    def calculate_salary(self, attendance_records: List[AttendanceRecord]):
        """Calculate comprehensive salary with allowances and taxes"""
        if self.days_worked == 0:
            self.net_salary = 0.0
            return
        
        # Calculate allowances (percentage of base salary)
        self.house_allowance = self.base_salary * 0.20  # 20% HRA
        self.transport_allowance = min(19200, self.base_salary * 0.10)  # 10% or max 19,200/year
        self.medical_allowance = self.base_salary * 0.15  # 15% medical
        self.other_allowances = self.base_salary * 0.05  # 5% other
        
        # Calculate gross salary
        self.gross_salary = (self.base_salary + self.house_allowance + 
                           self.transport_allowance + self.medical_allowance + 
                           self.other_allowances)
        
        # Attendance bonus for perfect attendance
        if self.days_worked >= 22:  # Assuming 22 working days per month
            self.attendance_bonus = self.base_salary * 0.05
        
        # Calculate taxes and deductions
        annual_gross = self.gross_salary * 12
        self.income_tax = self._calculate_income_tax(annual_gross) / 12  # Monthly tax
        
        self.provident_fund = self.base_salary * 0.12  # 12% PF
        self.professional_tax = self._calculate_professional_tax(self.gross_salary)
        
        # Other deductions (absent days)
        daily_rate = self.base_salary / 30
        absent_count = len([r for r in attendance_records if r.status == "Absent"])
        self.other_deductions = daily_rate * absent_count
        
        self.total_deductions = (self.income_tax + self.provident_fund + 
                               self.professional_tax + self.other_deductions)
        
        self.net_salary = self.gross_salary + self.attendance_bonus - self.total_deductions
        self.net_salary = max(0, self.net_salary)

    def _calculate_income_tax(self, annual_income: float) -> float:
        """Calculate annual income tax based on Indian tax slabs"""
        if annual_income <= 250000:
            return 0
        elif annual_income <= 500000:
            return (annual_income - 250000) * 0.05
        elif annual_income <= 1000000:
            return 12500 + (annual_income - 500000) * 0.20
        else:
            return 12500 + 100000 + (annual_income - 1000000) * 0.30

    def _calculate_professional_tax(self, monthly_gross: float) -> float:
        """Calculate professional tax based on salary"""
        if monthly_gross <= 3500:
            return 0
        elif monthly_gross <= 5000:
            return 27.50
        elif monthly_gross <= 6500:
            return 69
        else:
            return 2080  # Annual, but we'll divide by 12

    def approve_payroll(self, approved_by: str):
        """Approve the payroll record"""
        self.status = "Approved"
        self.approved_by = approved_by
        self.approved_date = datetime.datetime.now()

    def mark_as_paid(self):
        """Mark payroll as paid"""
        self.status = "Paid"

    def get_display_format(self) -> str:
        lines = [
            f"Employee: {self.employee_name} (ID: {self.employee_id})",
            f"Period: {self.month}/{self.year}",
            f"Status: {self.status}",
            "─" * 50,
            f"Base Salary:           Rs. {self.base_salary:>10,.2f}",
            f"House Allowance:       Rs. {self.house_allowance:>10,.2f}",
            f"Transport Allowance:   Rs. {self.transport_allowance:>10,.2f}",
            f"Medical Allowance:     Rs. {self.medical_allowance:>10,.2f}",
            f"Other Allowances:      Rs. {self.other_allowances:>10,.2f}",
            f"Gross Salary:          Rs. {self.gross_salary:>10,.2f}",
            "─" * 50,
            f"Attendance Bonus:      Rs. {self.attendance_bonus:>10,.2f}",
            f"Income Tax:            Rs. {self.income_tax:>10,.2f}",
            f"Provident Fund:        Rs. {self.provident_fund:>10,.2f}",
            f"Professional Tax:      Rs. {self.professional_tax:>10,.2f}",
            f"Other Deductions:      Rs. {self.other_deductions:>10,.2f}",
            f"Total Deductions:      Rs. {self.total_deductions:>10,.2f}",
            "─" * 50,
            f"NET SALARY:            Rs. {self.net_salary:>10,.2f}",
        ]
        if self.approved_by:
            lines.append(f"Approved by: {self.approved_by} on {self.approved_date.strftime('%Y-%m-%d')}")
        return "\n".join(lines)


class Payroll:
    def __init__(self, db_operations: DatabaseOperations):
        self.db_operations = db_operations
        self.records: List[PayrollRecord] = []
        self.employee_salaries: Dict[str, float] = {}  # employee_id -> base_salary
        self._load_from_db()

    def _load_from_db(self):
        if self.db_operations.connection is None:
            return
        self.employee_salaries.clear()
        self.records.clear()
        # Load salaries
        for row in self.db_operations.get_all_employee_salaries():
            self.employee_salaries[row['employee_id']] = float(row['base_salary'])
        # Load payroll records
        for row in self.db_operations.get_all_payroll_records():
            record = PayrollRecord(
                employee_id=row['employee_id'],
                employee_name=row['employee_name'],
                month=int(row['period_month']),
                year=int(row['period_year']),
                base_salary=float(row['base_salary']),
                days_worked=int(row['days_worked'])
            )
            record.attendance_bonus = float(row.get('attendance_bonus', 0))
            record.house_allowance = float(row.get('house_allowance', 0))
            record.transport_allowance = float(row.get('transport_allowance', 0))
            record.medical_allowance = float(row.get('medical_allowance', 0))
            record.other_allowances = float(row.get('other_allowances', 0))
            record.gross_salary = float(row.get('gross_salary', 0))
            record.income_tax = float(row.get('income_tax', 0))
            record.provident_fund = float(row.get('provident_fund', 0))
            record.professional_tax = float(row.get('professional_tax', 0))
            record.other_deductions = float(row.get('other_deductions', 0))
            record.total_deductions = float(row.get('total_deductions', 0))
            record.net_salary = float(row['net_salary'])
            record.status = row.get('status', 'Draft')
            record.approved_by = row.get('approved_by')
            if row.get('approved_date'):
                record.approved_date = row['approved_date']
            record.calculated_date = row['calculated_at']
            self.records.append(record)

    def set_employee_salary(self, employee_id: str, base_salary: float):
        self.employee_salaries[employee_id] = base_salary
        # Save to DB
        if self.db_operations.connection:
            self.db_operations.save_employee_salary(employee_id, base_salary)

    def generate_payroll(self, employee_id: str, month: int, year: int, 
                        attendance: 'Attendance') -> PayrollRecord:
        base_salary = self.employee_salaries.get(employee_id, 50000.0)
        attendance_records = attendance.get_employee_attendance(employee_id, month, year)
        days_worked = len([r for r in attendance_records if r.status in ["Present", "Half-day"]])
        
        employee_name = f"Employee {employee_id}"
        
        payroll_record = PayrollRecord(employee_id, employee_name, month, year, base_salary, days_worked)
        payroll_record.calculate_salary(attendance_records)
        
        self.records = [r for r in self.records if not (r.employee_id == employee_id and r.month == month and r.year == year)]
        self.records.append(payroll_record)
        
        if self.db_operations.connection:
            self.db_operations.save_payroll_record(
                employee_id,
                employee_name,
                month,
                year,
                base_salary,
                days_worked,
                payroll_record.attendance_bonus,
                payroll_record.house_allowance,
                payroll_record.transport_allowance,
                payroll_record.medical_allowance,
                payroll_record.other_allowances,
                payroll_record.gross_salary,
                payroll_record.income_tax,
                payroll_record.provident_fund,
                payroll_record.professional_tax,
                payroll_record.other_deductions,
                payroll_record.total_deductions,
                payroll_record.net_salary,
                payroll_record.status,
                payroll_record.approved_by,
                payroll_record.approved_date.isoformat() if isinstance(payroll_record.approved_date, datetime.datetime) else (payroll_record.approved_date if payroll_record.approved_date else None),
                payroll_record.calculated_date.isoformat()
            )
        
        return payroll_record

    def persist_record(self, payroll_record: PayrollRecord):
        if self.db_operations.connection:
            self.db_operations.save_payroll_record(
                payroll_record.employee_id,
                payroll_record.employee_name,
                payroll_record.month,
                payroll_record.year,
                payroll_record.base_salary,
                payroll_record.days_worked,
                payroll_record.attendance_bonus,
                payroll_record.house_allowance,
                payroll_record.transport_allowance,
                payroll_record.medical_allowance,
                payroll_record.other_allowances,
                payroll_record.gross_salary,
                payroll_record.income_tax,
                payroll_record.provident_fund,
                payroll_record.professional_tax,
                payroll_record.other_deductions,
                payroll_record.total_deductions,
                payroll_record.net_salary,
                payroll_record.status,
                payroll_record.approved_by,
                payroll_record.approved_date.isoformat() if isinstance(payroll_record.approved_date, datetime.datetime) else (payroll_record.approved_date if payroll_record.approved_date else None),
                payroll_record.calculated_date.isoformat()
            )

    def get_employee_payroll_history(self, employee_id: str) -> List[PayrollRecord]:
        return sorted([r for r in self.records if r.employee_id == employee_id], 
                     key=lambda r: (r.year, r.month))


class ChartRenderer:
    """Utility class for rendering ASCII charts in terminal"""
    
    @staticmethod
    def create_bar_chart(title: str, data: Dict[str, float], width: int = 40, height: int = 10) -> str:
        """Create ASCII bar chart"""
        if not data:
            return f"{title}\n[No data available]"
        
        lines = [f"\n{title}"]
        lines.append("=" * (width + 20))
        
        max_value = max(data.values()) if data.values() else 1
        if max_value == 0:
            max_value = 1
        
        for label, value in list(data.items())[:height]:
            bar_width = int((value / max_value) * width)
            bar = "█" * bar_width
            label_str = str(label)[:15].ljust(15)
            value_str = f"{value:.0f}".rjust(8)
            lines.append(f"{label_str} │{bar:<{width}}│ {value_str}")
        
        lines.append("=" * (width + 20))
        return "\n".join(lines)

    @staticmethod
    def create_line_chart(title: str, data_points: List[float], width: int = 40) -> str:
        """Create simple ASCII line chart"""
        if not data_points:
            return f"{title}\n[No data available]"
        
        lines = [f"\n{title}"]
        lines.append("=" * (width + 10))
        
        max_val = max(data_points) if data_points else 1
        min_val = min(data_points) if data_points else 0
        range_val = max_val - min_val if max_val != min_val else 1
        
        height = 8
        for row in range(height, 0, -1):
            line = ""
            for point in data_points[:width]:
                normalized = (point - min_val) / range_val
                row_height = int(normalized * height)
                if row_height >= row:
                    line += "█"
                else:
                    line += " "
            lines.append(f"│{line:<{width}}│")
        
        lines.append("=" * (width + 10))
        return "\n".join(lines)

    @staticmethod
    def create_pie_chart(title: str, data: Dict[str, float]) -> str:
        """Create ASCII pie chart representation"""
        if not data:
            return f"{title}\n[No data available]"
        
        lines = [f"\n{title}"]
        total = sum(data.values())
        if total == 0:
            total = 1
        
        for label, value in data.items():
            percentage = (value / total) * 100
            bar_length = int(percentage / 5)
            bar = "█" * bar_length
            label_str = str(label)[:15].ljust(15)
            lines.append(f"{label_str} {bar} {percentage:>5.1f}%")
        
        return "\n".join(lines)


class User(ABC):
    def __init__(self, id: str, name: str, email: str, role: str):
        self.id = id
        self.name = name
        self.email = email
        self.role = role
        self.permissions = self._get_role_permissions()

    def _get_role_permissions(self) -> Dict[str, bool]:
        """Define role permissions loaded from the database"""
        base_permissions = {
            "view_dashboard": True,
            "view_profile": True,
            "logout": True,
        }
        role = self.role.lower()
        if role in ROLE_PERMISSIONS_CACHE:
            return {**base_permissions, **ROLE_PERMISSIONS_CACHE[role]}
        return base_permissions

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        return self.permissions.get(permission, False)

    def display_info(self) -> str:
        return f"ID: {self.id} | Name: {self.name} | Role: {self.role}\nEmail: {self.email}"

    @abstractmethod
    def get_menu_options(self) -> List[str]:
        return ["DASHBOARD", "PROFILE", "LOGOUT"]

    @abstractmethod
    def handle_menu_choice(self, choice_index: int, ui: 'ConsoleUI', system: 'ILMSSystem'):
        selected_option = self.get_menu_options()[choice_index]
        if selected_option == "PROFILE":
            ui.handle_profile_update(self)
        elif selected_option == "LOGOUT":
            ui.user_logged_in = False

class Admin(User):
    def __init__(self, id: str, name: str, email: str):
        super().__init__(id, name, email, "Admin")
    
    def get_menu_options(self) -> List[str]:
        return [
            "DASHBOARD", 
            "Register Patient", "View All Patients", "Update Patient", "Delete Patient", "See Patient Report", "Manage Appointments",  
            "Review Results", "Track Samples", 
            "Approve Results", "Manage Inventory", "Staff Overview", "Performance Reports",
            "Perform Tests", "Track Sample Flow", "Equipment Logs",
            "Attendance Management", "Payroll Management", "Leave Management",
            "Business Metrics", "Custom Reports", "Manage Finances", "Compliance", 
            "HELP", "PROFILE", "LOGOUT"
        ]

    def handle_menu_choice(self, choice_index: int, ui: 'ConsoleUI', system: 'ILMSSystem'):
        opt = self.get_menu_options()[choice_index]
        
        if opt == "Register Patient": ui.handle_patient_registration()
        elif opt == "View All Patients": ui.handle_view_all_patients()
        elif opt == "Update Patient": ui.handle_update_patient()
        elif opt == "Delete Patient": ui.handle_delete_patient()
        elif opt == "See Patient Report": ui.handle_see_patient_reports()
        elif opt == "Manage Appointments": ui.handle_manage_appointments()
        elif opt == "Review Results": ui.handle_review_results(self.id)
        elif opt == "Track Samples": ui.handle_track_samples()
        elif opt == "Approve Results": ui.handle_approve_results()
        elif opt == "Manage Inventory": ui.handle_manage_inventory()
        elif opt == "Staff Overview": ui.handle_view_staff()
        elif opt == "Performance Reports": ui.handle_view_performance_reports()
        elif opt == "Perform Tests": ui.handle_perform_tests()
        elif opt == "Track Sample Flow": ui.handle_track_sample_flow()
        elif opt == "Equipment Logs": ui.handle_equipment_logs()
        elif opt == "Business Metrics": ui.handle_view_metrics()
        elif opt == "Manage Finances": ui.handle_view_finances()
        elif opt == "Compliance": ui.handle_view_compliance()
        elif opt == "Attendance Management": ui.handle_attendance_management()
        elif opt == "Payroll Management": ui.handle_payroll_management()
        elif opt == "Leave Management": ui.handle_leave_management()
        elif opt == "Custom Reports": ui.handle_custom_reports()
        elif opt == "HELP": ui.handle_help()
        else: super().handle_menu_choice(choice_index, ui, system)

class Owner(User):
    def __init__(self, id: str, name: str, email: str):
        super().__init__(id, name, email, "Owner")
    def get_menu_options(self) -> List[str]:
        return ["DASHBOARD", "Business Metrics", "Manage Finances", "Attendance Management", 
                "Payroll Management", "Leave Management", "Compliance", "Operations Report", "PROFILE", "LOGOUT"]
    def handle_menu_choice(self, choice_index: int, ui: 'ConsoleUI', system: 'ILMSSystem'):
        opt = self.get_menu_options()[choice_index]
        if opt == "Business Metrics": ui.handle_view_metrics()
        elif opt == "Manage Finances": ui.handle_view_finances()
        elif opt == "Compliance": ui.handle_view_compliance()
        elif opt == "Attendance Management": ui.handle_attendance_management()
        elif opt == "Payroll Management": ui.handle_payroll_management()
        elif opt == "Leave Management": ui.handle_leave_management()
        elif opt == "Operations Report": ui.handle_view_operations_report()
        else: super().handle_menu_choice(choice_index, ui, system)

class LabManager(User):
    def __init__(self, id: str, name: str, email: str):
        super().__init__(id, name, email, "Lab Manager")
    def get_menu_options(self) -> List[str]:
        return ["DASHBOARD", "Approve Results", "Manage Inventory", "Staff Overview", "Performance Reports", "PROFILE", "LOGOUT"]
    def handle_menu_choice(self, choice_index: int, ui: 'ConsoleUI', system: 'ILMSSystem'):
        opt = self.get_menu_options()[choice_index]
        if opt == "Approve Results": ui.handle_approve_results()
        elif opt == "Manage Inventory": ui.handle_manage_inventory()
        elif opt == "Staff Overview": ui.handle_view_staff()
        elif opt == "Performance Reports": ui.handle_view_performance_reports()
        else: super().handle_menu_choice(choice_index, ui, system)

class Receptionist(User):
    def __init__(self, id: str, name: str, email: str):
        super().__init__(id, name, email, "Receptionist")
    def get_menu_options(self) -> List[str]:
        return ["DASHBOARD", "Register Patient", "View All Patients", "Update Patient", "See Patient Report", "Manage Appointments", "Verify ID", "Sample Submissions", "Request Leave", "PROFILE", "LOGOUT"]
    def handle_menu_choice(self, choice_index: int, ui: 'ConsoleUI', system: 'ILMSSystem'):
        opt = self.get_menu_options()[choice_index]
        if opt == "Register Patient": ui.handle_patient_registration()
        elif opt == "View All Patients": ui.handle_view_all_patients()
        elif opt == "Update Patient": ui.handle_update_patient()
        elif opt == "See Patient Report": ui.handle_see_patient_reports()
        elif opt == "Manage Appointments": ui.handle_manage_appointments()
        elif opt == "Verify ID": ui.handle_verify_id()
        elif opt == "Sample Submissions": ui.handle_sample_submissions()
        elif opt == "Request Leave": ui.handle_request_leave()
        else: super().handle_menu_choice(choice_index, ui, system)

class Doctor(User):
    def __init__(self, id: str, name: str, email: str):
        super().__init__(id, name, email, "Doctor")
    def get_menu_options(self) -> List[str]:
        return ["DASHBOARD", "Review Results", "Track Samples", "Request Leave", "PROFILE", "LOGOUT"]
    def handle_menu_choice(self, choice_index: int, ui: 'ConsoleUI', system: 'ILMSSystem'):
        opt = self.get_menu_options()[choice_index]
        if opt == "Review Results": ui.handle_review_results(self.id)
        elif opt == "Track Samples": ui.handle_track_samples()
        elif opt == "Request Leave": ui.handle_request_leave()
        else: super().handle_menu_choice(choice_index, ui, system)

class LabTechnician(User):
    def __init__(self, id: str, name: str, email: str):
        super().__init__(id, name, email, "Lab Technician")
    def get_menu_options(self) -> List[str]:
        return ["DASHBOARD", "Perform Tests", "Track Sample Flow", "Equipment Logs", "Request Leave", "PROFILE", "LOGOUT"]
    def handle_menu_choice(self, choice_index: int, ui: 'ConsoleUI', system: 'ILMSSystem'):
        opt = self.get_menu_options()[choice_index]
        if opt == "Perform Tests": ui.handle_perform_tests()
        elif opt == "Track Sample Flow": ui.handle_track_sample_flow()
        elif opt == "Equipment Logs": ui.handle_equipment_logs()
        elif opt == "Request Leave": ui.handle_request_leave()
        else: super().handle_menu_choice(choice_index, ui, system)

class Patient(User):
    def __init__(self, id: str, name: str, email: str):
        super().__init__(id, name, email, "Patient")
        self.tests_ordered: List[Test] = []
        self.invoices: List['Invoice'] = []
        self.messages: List[str] = ["Welcome to ILMS!"]

    def get_menu_options(self) -> List[str]:
        return []
    def handle_menu_choice(self, choice_index: int, ui: 'ConsoleUI', system: 'ILMSSystem'):
        pass

class UserFactory:
    _role_classes: Dict[str, Type[User]] = {
        "owner": Owner, "lab manager": LabManager, "receptionist": Receptionist,
        "doctor": Doctor, "lab technician": LabTechnician, "patient": Patient,
        "admin": Admin 
    }

    @staticmethod
    def create_user(role: str, **kwargs: Any) -> User:
        role_key = role.lower()
        user_class = UserFactory._role_classes.get(role_key)
        if not user_class: raise ValueError(f"Unknown user role: {role}")
        
        if 'id' not in kwargs and role_key != 'patient':
            prefix = "ADM" if role_key == "admin" else role_key[0].upper()
            if role_key == "lab manager": prefix = "LM"
            if role_key == "lab technician": prefix = "LT"
            
            time_comp = int(time.time() * 100) % 100000
            kwargs['id'] = f"{prefix}{time_comp}"
            
        return user_class(**kwargs)

class ILMSSystem:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.db_operations = DatabaseOperations(self.db_manager)
        self.users: Dict[str, User] = {}
        self.patients: Dict[str, Patient] = {}
        self.test_groups: Dict[str, TestGroup] = {}
        self.invoices: List[Invoice] = []
        self.inventory: Dict[str, int] = {}
        self.finances: Dict[str, float] = {}
        self.equipment_logs: List[str] = []
        self.compliance_reports: List[str] = []
        self.appointments: List[str] = []
        self.logged_in_user: Optional[User] = None
        self.attendance: Attendance = Attendance(self.db_operations)
        self.payroll: Payroll = Payroll(self.db_operations)
        self.employees: Dict[str, User] = {}  # Staff employees (non-patients)
        self.daily_revenue_history: Dict[str, float] = {}  # date -> revenue
        self.test_completion_history: List[int] = []  # Daily test completions
        self.leave_types: Dict[int, LeaveType] = {}
        self.leave_requests: List[LeaveRequest] = []
        self.leave_balances: Dict[str, LeaveBalance] = {}
        self.leave_manager: LeaveManager = LeaveManager(self.db_operations)
        self.role_permissions: Dict[str, Dict[str, bool]] = {}
        self.load_data()

    def load_data(self):
        if self.db_operations.connection:
            self._load_role_permissions_from_db()
            self._load_data_from_db()
        self.logged_in_user = None

    def _load_role_permissions_from_db(self):
        if self.db_operations.connection is None:
            return
        self.role_permissions.clear()
        for row in self.db_operations.get_all_role_permissions():
            role_name = row['role_name'].lower()
            self.role_permissions.setdefault(role_name, {})
            self.role_permissions[role_name][row['permission']] = bool(row['allowed'])
        ROLE_PERMISSIONS_CACHE.clear()
        ROLE_PERMISSIONS_CACHE.update(self.role_permissions)

    def save_data(self):
        if self.db_operations.connection:
            try:
                self.db_operations.commit()
            except Exception:
                pass

    def _load_data_from_db(self):
        if self.db_operations.connection is None:
            return

        self.users.clear()
        self.patients.clear()
        self.employees.clear()
        self.test_groups.clear()
        self.invoices.clear()
        self.inventory.clear()
        self.equipment_logs.clear()
        self.compliance_reports.clear()
        self.appointments.clear()
        self.daily_revenue_history.clear()

        # Load users
        for row in self.db_operations.get_all_users():
            try:
                user = UserFactory.create_user(row['role'], id=row['id'], name=row['name'], email=row['email'])
                user.permissions = self.role_permissions.get(user.role.lower(), user.permissions)
                user.password_hash = row.get('password_hash')
                user.password_salt = row.get('password_salt')
                self.users[user.id] = user
                if row['role'].lower() != 'patient':
                    self.employees[user.id] = user
                else:
                    self.patients[user.id] = user
            except Exception:
                continue

        # Load patients
        for row in self.db_operations.get_all_patients():
            patient = UserFactory.create_user('patient', id=row['id'], name=row['name'], email=row['email'])
            patient.permissions = self.role_permissions.get(patient.role.lower(), patient.permissions)
            self.patients[patient.id] = patient
            self.users[patient.id] = patient

        # Load specimens and test groups
        specimens: Dict[str, Specimen] = {}
        for row in self.db_operations.get_all_specimens():
            specimens[row['id']] = Specimen(row['id'], row['specimen_type'], row['storage_conditions'])

        for row in self.db_operations.get_all_test_groups():
            group = TestGroup(row['id'], row['group_name'])
            self.test_groups[group.id] = group

        # Load tests
        tests: Dict[str, Test] = {}
        for row in self.db_operations.get_all_tests():
            specimen = specimens.get(row['specimen_id'])
            if specimen is None:
                continue
            test = Test(
                id=row['id'],
                name=row['name'],
                price=float(row['price']),
                test_group_name=row['test_group_id'],
                specimen=specimen
            )
            test.status = row['status']
            test.result = row.get('result')
            test.patient_id = row.get('patient_id')
            test.technician_id = row.get('technician_id')
            tests[test.id] = test
            group = self.test_groups.get(row['test_group_id'])
            if group:
                if test not in group.tests:
                    group.tests.append(test)

        for test in tests.values():
            if test.patient_id and test.patient_id in self.patients:
                self.patients[test.patient_id].tests_ordered.append(test)

        # Load invoices
        invoice_map: Dict[str, Invoice] = {}
        for row in self.db_operations.get_all_invoices():
            invoice = Invoice(row['id'], row['patient_id'], row['patient_name'], [])
            invoice.date = row['date'] if isinstance(row['date'], datetime.datetime) else datetime.datetime.fromisoformat(row['date'])
            invoice.total_amount = float(row['total_amount'])
            invoice.fbr_code = row['fbr_code']
            invoice_map[invoice.id] = invoice
            self.invoices.append(invoice)
            if invoice.patient_id in self.patients:
                self.patients[invoice.patient_id].invoices.append(invoice)

        for row in self.db_operations.get_all_invoice_tests():
            invoice = invoice_map.get(row['invoice_id'])
            test = tests.get(row['test_id'])
            if invoice and test:
                invoice.tests.append(test)

        # Load inventory and operational records
        for row in self.db_operations.get_all_inventory():
            self.inventory[row['item_name']] = int(row['quantity'])

        for row in self.db_operations.get_all_equipment_logs():
            entry = f"{row['entry_date']} - {row['entry']}"
            self.equipment_logs.append(entry)

        for row in self.db_operations.get_all_compliance_reports():
            entry = f"{row['created_at']} - {row['report_text']}"
            self.compliance_reports.append(entry)

        for row in self.db_operations.get_all_appointments():
            appointment_time = row['appointment_datetime'] if isinstance(row['appointment_datetime'], datetime.datetime) else datetime.datetime.fromisoformat(row['appointment_datetime'])
            self.appointments.append(f"{appointment_time.strftime('%Y-%m-%d %H:%M')} - {row['patient_name']}")

        for row in self.db_operations.get_all_daily_revenue():
            date_value = row['revenue_date'] if isinstance(row['revenue_date'], datetime.date) else datetime.date.fromisoformat(row['revenue_date'])
            self.daily_revenue_history[date_value.isoformat()] = float(row['revenue'])

        self.finances['Total Revenue'] = sum(self.daily_revenue_history.values())
        self.finances['Total Expenses'] = self.finances.get('Total Expenses', 0.0)
        self.leave_types = self.leave_manager.leave_types
        self.leave_requests = self.leave_manager.leave_requests
        self.leave_balances = self.leave_manager.leave_balances

    def attempt_login(self, username: str, password: str) -> bool:
        for user in self.users.values():
            if user.name.lower() == username.lower():
                if getattr(user, 'password_hash', None) and getattr(user, 'password_salt', None):
                    if verify_password(password, user.password_salt, user.password_hash):
                        self.logged_in_user = user
                        return True
                elif password == "123":
                    self.logged_in_user = user
                    return True
        return False

    def register_patient_logic(self, name: str, email: str) -> Patient:
        patient_id = f"P{len(self.patients) + 1001}"
        new_patient = UserFactory.create_user("patient", id=patient_id, name=name, email=email)
        if isinstance(new_patient, Patient):
            self.patients[new_patient.id] = new_patient
            self.users[new_patient.id] = new_patient
            if self.db_operations.connection:
                salt, password_hash = hash_password("123")
                self.db_operations.save_user(
                    new_patient.id,
                    new_patient.name,
                    new_patient.email,
                    new_patient.role,
                    1,
                    password_hash,
                    salt
                )
                self.db_operations.save_patient(new_patient.id, new_patient.name, new_patient.email)
            return new_patient
        raise TypeError("Could not create Patient object.")

    def generate_invoice_logic(self, patient: Patient, tests: List[Test]) -> Invoice:
        invoice_id = f"INV-{int(time.time())}"
        new_invoice = Invoice(id=invoice_id, patient_id=patient.id, patient_name=patient.name, tests=tests)
        self.invoices.append(new_invoice)
        patient.invoices.append(new_invoice)
        if self.db_operations.connection:
            self.db_operations.save_invoice(
                invoice_id,
                patient.id,
                patient.name,
                datetime.datetime.now().isoformat(),
                sum(test.price for test in tests),
                new_invoice.fbr_code
            )

        for test in tests:
            test.patient_id = patient.id
            patient.tests_ordered.append(test)
            if self.db_operations.connection:
                self.db_operations.save_test(
                    test.id,
                    test.name,
                    test.price,
                    test.test_group_name,
                    test.specimen.id,
                    test.status,
                    test.result,
                    test.patient_id,
                    test.technician_id
                )
                self.db_operations.save_invoice_test(invoice_id, test.id)
            if "Total Revenue" not in self.finances: self.finances["Total Revenue"] = 0.0
            self.finances["Total Revenue"] += test.price
        return new_invoice

    def get_business_metrics(self) -> Dict[str, float]:
        metrics = self.finances.copy()
        metrics["Profit"] = metrics.get("Total Revenue", 0.0) - metrics.get("Total Expenses", 0.0)
        metrics["Total Patients"] = float(len(self.patients))
        return metrics

    def get_employee_performance_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics for all employees"""
        metrics = {}
        today = datetime.date.today()
        
        for emp_id, emp in self.employees.items():
            # Attendance metrics
            attendance_summary = self.attendance.get_attendance_summary(emp_id, today.month, today.year)
            
            # Payroll metrics (last 3 months)
            payroll_history = self.payroll.get_employee_payroll_history(emp_id)[-3:]
            avg_salary = sum(r.net_salary for r in payroll_history) / len(payroll_history) if payroll_history else 0
            
            # Leave metrics
            leave_balance = self.leave_manager.get_leave_balance(emp_id)
            # Use the attribute names defined in LeaveBalance
            leave_used = (leave_balance.used_annual + leave_balance.used_sick) if leave_balance else 0
            
            metrics[emp_id] = {
                "name": emp.name,
                "role": emp.role,
                "attendance_rate": (attendance_summary.get('total_present', 0) / 30) * 100 if attendance_summary.get('total_present', 0) > 0 else 0,
                "average_salary": avg_salary,
                "leave_used": leave_used,
                "performance_score": self._calculate_performance_score(attendance_summary, avg_salary, leave_used)
            }
        
        return metrics

    def _calculate_performance_score(self, attendance: Dict[str, Any], avg_salary: float, leave_used: int) -> float:
        """Calculate employee performance score (0-100)"""
        attendance_score = min(100, (attendance['total_present'] / 22) * 100)  # 22 working days
        salary_score = min(100, avg_salary / 100000 * 100)  # Normalize to 100k
        leave_score = max(0, 100 - (leave_used / 30) * 100)  # Penalize excessive leave
        
        return (attendance_score * 0.4 + salary_score * 0.4 + leave_score * 0.2)

    def get_real_time_analytics(self) -> Dict[str, Any]:
        """Get real-time analytics data"""
        today = datetime.date.today()
        
        # Revenue analytics
        monthly_revenue = sum(self.daily_revenue_history.values()) if self.daily_revenue_history else 0
        daily_avg = monthly_revenue / len(self.daily_revenue_history) if self.daily_revenue_history else 0
        
        # Test analytics
        total_tests = sum(len(p.tests_ordered) for p in self.patients.values())
        completed_tests = len(self.get_tests_by_status("Completed"))
        pending_tests = len(self.get_tests_by_status("Pending"))
        
        # Employee analytics
        total_employees = len(self.employees)
        active_employees = len([e for e in self.employees.values() if hasattr(e, 'active') and e.active])
        
        # Leave analytics
        pending_leaves = len(self.leave_manager.get_pending_requests()) if hasattr(self, 'leave_manager') else 0
        
        return {
            "revenue": {
                "monthly_total": monthly_revenue,
                "daily_average": daily_avg,
                "growth_rate": self._calculate_growth_rate()
            },
            "tests": {
                "total": total_tests,
                "completed": completed_tests,
                "pending": pending_tests,
                "completion_rate": (completed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            "employees": {
                "total": total_employees,
                "active": active_employees,
                "utilization_rate": (active_employees / total_employees * 100) if total_employees > 0 else 0
            },
            "leave": {
                "pending_requests": pending_leaves
            }
        }

    def _calculate_growth_rate(self) -> float:
        """Calculate revenue growth rate"""
        if len(self.daily_revenue_history) < 2:
            return 0.0
        
        values = list(self.daily_revenue_history.values())
        recent = sum(values[-7:])  # Last 7 days
        previous = sum(values[-14:-7])  # Previous 7 days
        
        if previous == 0:
            return 0.0
        
        return ((recent - previous) / previous) * 100

    def generate_custom_report(self, report_type: str, filters: Dict[str, Any] = None) -> str:
        """Generate custom reports"""
        if report_type == "employee_summary":
            return self._generate_employee_summary_report(filters)
        elif report_type == "financial_summary":
            return self._generate_financial_summary_report(filters)
        elif report_type == "test_performance":
            return self._generate_test_performance_report(filters)
        else:
            return "Unknown report type"

    def _generate_employee_summary_report(self, filters: Dict[str, Any] = None) -> str:
        """Generate employee summary report"""
        lines = ["EMPLOYEE SUMMARY REPORT", "=" * 50]
        
        for emp_id, emp in self.employees.items():
            lines.append(f"Name: {emp.name}")
            lines.append(f"ID: {emp_id}")
            lines.append(f"Role: {emp.role}")
            
            # Add performance metrics if available
            perf_metrics = self.get_employee_performance_metrics().get(emp_id, {})
            if perf_metrics:
                lines.append(f"Attendance Rate: {perf_metrics.get('attendance_rate', 0):.1f}%")
                lines.append(f"Average Salary: Rs. {perf_metrics.get('average_salary', 0):,.2f}")
                lines.append(f"Performance Score: {perf_metrics.get('performance_score', 0):.1f}/100")
            lines.append("-" * 30)
        
        return "\n".join(lines)

    def _generate_financial_summary_report(self, filters: Dict[str, Any] = None) -> str:
        """Generate financial summary report"""
        metrics = self.get_business_metrics()
        lines = ["FINANCIAL SUMMARY REPORT", "=" * 50]
        
        lines.append(f"Total Revenue: Rs. {metrics.get('Total Revenue', 0):,.2f}")
        lines.append(f"Total Expenses: Rs. {metrics.get('Total Expenses', 0):,.2f}")
        lines.append(f"Profit: Rs. {metrics.get('Profit', 0):,.2f}")
        lines.append(f"Total Patients: {int(metrics.get('Total Patients', 0))}")
        
        return "\n".join(lines)

    def _generate_test_performance_report(self, filters: Dict[str, Any] = None) -> str:
        """Generate test performance report"""
        analytics = self.get_real_time_analytics()
        lines = ["TEST PERFORMANCE REPORT", "=" * 50]
        
        test_data = analytics.get('tests', {})
        lines.append(f"Total Tests: {test_data.get('total', 0)}")
        lines.append(f"Completed Tests: {test_data.get('completed', 0)}")
        lines.append(f"Pending Tests: {test_data.get('pending', 0)}")
        lines.append(f"Completion Rate: {test_data.get('completion_rate', 0):.1f}%")
        
        return "\n".join(lines)

    def get_tests_by_status(self, status: str) -> List[Test]:
        tests = []
        for p in self.patients.values():
            for t in p.tests_ordered:
                if t.status == status:
                    tests.append(t)
        return tests

    def get_patient_by_id(self, patient_id: str) -> Optional[Patient]:
        return self.patients.get(patient_id)
        
    def handle_db_connection_failure(self) -> bool:
        """Handle database connection failure during runtime"""
        return self.db_manager.handle_connection_failure()
        
    def add_appointment(self, date: str, time: str, name: str) -> bool:
        try:
            appointment_dt = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
            self.appointments.append(f"{date} {time} - {name}")
            if self.db_operations.connection:
                self.db_operations.save_appointment(appointment_dt, name, 'Scheduled')
            return True
        except ValueError:
            return False

class ConsoleUI:
    def __init__(self, system: ILMSSystem):
        self.system = system
        self.stdscr: Optional[curses.window] = None
        self.sidebar_menu: List[str] = []
        self.sidebar_selection = 0
        self.app_running = True
        self.user_logged_in = False

    def _calculate_worked_hours(self, check_in: Optional[datetime.time], check_out: Optional[datetime.time], status: str) -> float:
        """Calculate worked hours for attendance"""
        if check_in and check_out and status == "Present":
            dt_checkin = datetime.datetime.combine(datetime.date.today(), check_in)
            dt_checkout = datetime.datetime.combine(datetime.date.today(), check_out)
            delta = dt_checkout - dt_checkin
            return delta.total_seconds() / 3600
        elif status == "Half-day":
            return 4.0
        return 0.0

    def run(self, stdscr: curses.window):
        self.stdscr = stdscr
        curses.curs_set(0)
        self.stdscr.nodelay(1) 
        self.stdscr.timeout(100)

        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)      # Default
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)      # Highlight
        curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)        # Accent
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)       # Success
        curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)         # Error
        curses.init_pair(6, curses.COLOR_YELLOW, curses.COLOR_BLACK)      # Warning
        curses.init_pair(7, curses.COLOR_MAGENTA, curses.COLOR_BLACK)     # Special
        curses.init_pair(8, curses.COLOR_BLUE, curses.COLOR_BLACK)        # Info
        
        self.stdscr.bkgd(' ', curses.color_pair(1))

        while self.app_running:
            if not self.user_logged_in:
                self.handle_splash_screen()
            
            if self.user_logged_in:
                if self.system.logged_in_user:
                    self.sidebar_menu = self.system.logged_in_user.get_menu_options()
                    self.main_app_loop()
                else:
                    self.user_logged_in = False
        
        self.system.save_data()

    def main_app_loop(self):
        self.sidebar_selection = 0
        self.stdscr.clear() 
        
        while self.user_logged_in:
            self.draw_dashboard_layout()
            self.draw_sidebar_menu()
            self.stdscr.refresh()
            
            key = self.stdscr.getch()
            if key != -1: 
                self.handle_main_input(key)

    def handle_splash_screen(self):
        options = ["Login", "Exit"]
        current_selection = 0
        
        while not self.user_logged_in and self.app_running:
            self.stdscr.erase() 
            h, w = self.stdscr.getmaxyx()
            
            title = "ILMS"
            self.stdscr.addstr(h // 2 - 5, (w - len(title)) // 2, title, curses.color_pair(3) | curses.A_BOLD)

            for i, option in enumerate(options):
                attr = curses.color_pair(1)
                if i == current_selection:
                    attr = curses.color_pair(2)
                self.stdscr.addstr(h // 2 + i, (w - len(option)) // 2, option, attr)

            self.stdscr.refresh()
            
            key = self.stdscr.getch()

            if key == curses.KEY_UP:
                current_selection = (current_selection - 1) % len(options)
            elif key == curses.KEY_DOWN:
                current_selection = (current_selection + 1) % len(options)
            elif key == curses.KEY_ENTER or key == 10:
                if current_selection == 0:
                    if self.handle_login():
                        self.user_logged_in = True
                elif current_selection == 1:
                    self.app_running = False
            elif key == 27:
                self.app_running = False

    def handle_main_input(self, key: int):
        # Keyboard shortcuts
        if key == ord('q') or key == ord('Q'):
            self.app_running = False
            return
        elif key == ord('d') or key == ord('D'):
            # Quick dashboard access
            if "DASHBOARD" in self.sidebar_menu:
                idx = self.sidebar_menu.index("DASHBOARD")
                self.system.logged_in_user.handle_menu_choice(idx, self, self.system)
                self.stdscr.clear()
            return
        elif key == ord('l') or key == ord('L'):
            # Quick logout
            if "LOGOUT" in self.sidebar_menu:
                idx = self.sidebar_menu.index("LOGOUT")
                self.system.logged_in_user.handle_menu_choice(idx, self, self.system)
                self.stdscr.clear()
            return
        
        # Navigation
        if key == curses.KEY_UP:
            self.sidebar_selection = (self.sidebar_selection - 1) % len(self.sidebar_menu)
        elif key == curses.KEY_DOWN:
            self.sidebar_selection = (self.sidebar_selection + 1) % len(self.sidebar_menu)
        elif key == curses.KEY_ENTER or key == 10 or key == ord(' '):
            if self.system.logged_in_user:
                self.system.logged_in_user.handle_menu_choice(
                    self.sidebar_selection, self, self.system
                )
                self.stdscr.clear() 

    def draw_dashboard_layout(self):
        h, w = self.stdscr.getmaxyx()
        
        login_time = datetime.datetime.now().strftime('%H:%M')
        header = f"ILMS | Time: {login_time}".ljust(w)
        self.stdscr.addstr(0, 0, header, curses.A_REVERSE)
        
        user_name = self.system.logged_in_user.name
        self.stdscr.addstr(2, 30, f"USER: {user_name} ({self.system.logged_in_user.role})")
        self.stdscr.addstr(3, 30, "--------------------")

        sidebar_width = 28
        for y in range(1, h - 1): self.stdscr.addstr(y, sidebar_width, "|")
        self.stdscr.addstr(h - 2, 0, "=" * (w - 1))

        def draw_box(y, x, h, w, title, content_lines):
            self.stdscr.attron(curses.color_pair(3))
            self.stdscr.addstr(y, x + 2, f" {title} ")
            self.stdscr.attroff(curses.color_pair(3))
            self.stdscr.hline(y, x + 1, curses.ACS_HLINE, w - 2)
            self.stdscr.hline(y + h - 1, x + 1, curses.ACS_HLINE, w - 2)
            self.stdscr.vline(y + 1, x, curses.ACS_VLINE, h - 2)
            self.stdscr.vline(y + 1, x + w - 1, curses.ACS_VLINE, h - 2)
            self.stdscr.addch(y, x, curses.ACS_ULCORNER)
            self.stdscr.addch(y, x + w - 1, curses.ACS_URCORNER)
            self.stdscr.addch(y + h - 1, x, curses.ACS_LLCORNER)
            self.stdscr.addch(y + h - 1, x + w - 1, curses.ACS_LRCORNER)
            
            for i, line in enumerate(content_lines):
                if i < h - 2:
                    self.stdscr.addstr(y + 1 + i, x + 2, line[:w-4])

        if self.system.logged_in_user.__class__.__name__ in ['Admin', 'Owner']:
            rev = self.system.finances.get('Total Revenue', 0.0)
            exp = self.system.finances.get('Total Expenses', 0.0)
            draw_box(5, 32, 10, 25, "FINANCIALS", [
                f"Revenue: Rs.{rev:.2f}",
                f"Expense: Rs.{exp:.2f}",
                f"Net:     Rs.{rev-exp:.2f}"
            ])
            
            low_stock = [k for k, v in self.system.inventory.items() if v < 50]
            inv_lines = [f"{k}: {self.system.inventory[k]}" for k in low_stock[:5]]
            if not inv_lines: inv_lines = ["All Stock Healthy"]
            draw_box(5, 60, 10, 25, "LOW STOCK ALERTS", inv_lines)
            
            pending = len(self.system.get_tests_by_status("Pending"))
            progress = len(self.system.get_tests_by_status("In Progress"))
            approve = len(self.system.get_tests_by_status("Completed"))
            draw_box(16, 32, 6, 53, "WORK QUEUE", [
                f"Pending Admission: {pending}",
                f"In Lab Analysis:   {progress}",
                f"Awaiting Approval: {approve}"
            ])
            
            # Revenue Chart
            if w > 80:
                revenue_data = {}
                for date_str, amount in list(self.system.daily_revenue_history.items())[-7:]:
                    date_obj = datetime.date.fromisoformat(date_str)
                    revenue_data[date_obj.strftime('%m/%d')] = amount
                if revenue_data:
                    chart_lines = ChartRenderer.create_line_chart("Revenue (Last 7 Days)", list(revenue_data.values()), min(40, w-50)).split('\n')
                    for i, line in enumerate(chart_lines[:8]):
                        if 23 + i < h - 2:
                            self.stdscr.addstr(23 + i, 32, line[:min(48, w-34)])
            
            # Test Status Pie Chart
            if w > 80:
                test_status_data = {
                    "Pending": len(self.system.get_tests_by_status("Pending")),
                    "In Progress": len(self.system.get_tests_by_status("In Progress")),
                    "Completed": len(self.system.get_tests_by_status("Completed")),
                    "Approved": len(self.system.get_tests_by_status("Approved"))
                }
                pie_chart = ChartRenderer.create_pie_chart("Test Status", test_status_data)
                pie_lines = pie_chart.split('\n')
                for i, line in enumerate(pie_lines[:10]):
                    if 5 + i < h - 2 and 88 + len(line) < w:
                        self.stdscr.addstr(5 + i, 88, line)
            
        else:
            draw_box(5, 35, 8, 30, "NOTIFICATIONS", ["System Normal", "No new alerts."])

    def draw_sidebar_menu(self):
        for i, item in enumerate(self.sidebar_menu):
            y = i + 2
            x = 2
            prefix = " >" if i == self.sidebar_selection else "  "
            attr = curses.color_pair(2) if i == self.sidebar_selection else curses.color_pair(1)
            display_item = item.ljust(22)
            self.stdscr.addstr(y, x, f"{prefix} {display_item[:22]}", attr)
            
    def _create_modal_window(self, h: int, w: int, title: str) -> curses.window:
        max_h, max_w = self.stdscr.getmaxyx()
        start_y = (max_h - h) // 2
        start_x = (max_w - w) // 2
        win = curses.newwin(h, w, start_y, start_x)
        win.bkgd(' ', curses.color_pair(2))
        win.attron(curses.color_pair(2))
        win.border()
        win.addstr(0, (w - len(title) - 2) // 2, f" {title} ")
        win.attroff(curses.color_pair(2))
        win.attron(curses.color_pair(1))
        win.keypad(True) 
        return win

    def display_message(self, title: str, message: str):
        lines = message.split('\n')
        h = len(lines) + 4
        w = max(40, max([len(line) for line in lines] or [0]) + 6)
        win = self._create_modal_window(h, w, title)
        for i, line in enumerate(lines):
            win.addstr(i + 2, 2, line, curses.color_pair(2))
        win.refresh()
        win.getch()
        del win

    def get_input(self, title: str, prompt: str) -> Optional[str]:
        h = 5
        w = max(40, len(prompt) + 20)
        win = self._create_modal_window(h, w, title)
        win.addstr(2, 2, prompt, curses.color_pair(2))
        curses.curs_set(1)
        curses.echo()
        win.attron(curses.color_pair(2))
        try:
            input_str = win.getstr(2, 2 + len(prompt), w - len(prompt) - 4).decode('utf-8')
        except curses.error: input_str = None
        win.attroff(curses.color_pair(2))
        curses.noecho()
        curses.curs_set(0)
        del win
        return input_str

    def navigate_menu_modal(self, title: str, options: List[str]) -> int:
        h = len(options) + 4
        w = max(40, max([len(opt) for opt in options] or [0]) + 8)
        win = self._create_modal_window(h, w, title)
        current_opt = 0
        while True:
            for i, option in enumerate(options):
                attr = curses.color_pair(2)
                prefix = "  "
                if i == current_opt:
                    prefix = "> "
                    attr = curses.A_REVERSE | curses.color_pair(2)
                win.addstr(i + 2, 2, f"{prefix}{option}", attr)
            win.refresh()
            key = win.getch()
            if key == curses.KEY_UP: current_opt = (current_opt - 1) % len(options)
            elif key == curses.KEY_DOWN: current_opt = (current_opt + 1) % len(options)
            elif key == curses.KEY_ENTER or key == 10: return current_opt
            elif key == 27: return -1

    def navigate_multi_select_modal(self, title: str, options: List[str]) -> List[int]:
        h = len(options) + 5
        w = max(40, max([len(opt) for opt in options] or [0]) + 10)
        win = self._create_modal_window(h, w, title)
        current_opt = 0
        selected = [False] * len(options)
        win.addstr(h - 2, 2, "SPACE to toggle, ENTER to confirm.", curses.color_pair(2))
        while True:
            for i, option in enumerate(options):
                attr = curses.color_pair(2)
                cursor = " "
                checkbox = "[ ]"
                if i == current_opt:
                    cursor = ">"
                    attr = curses.A_REVERSE | curses.color_pair(2)
                if selected[i]: checkbox = "[x]"
                win.addstr(i + 2, 2, f"{cursor} {checkbox} {option}", attr)
            win.refresh()
            key = win.getch()
            if key == curses.KEY_UP: current_opt = (current_opt - 1) % len(options)
            elif key == curses.KEY_DOWN: current_opt = (current_opt + 1) % len(options)
            elif key == 32: selected[current_opt] = not selected[current_opt]
            elif key == curses.KEY_ENTER or key == 10: return [i for i, s in enumerate(selected) if s]
            elif key == 27: return []

    def handle_login(self) -> bool:
        while True:
            username = self.get_input("Login", "Username (admin, owner, labtech, receptionist, doctor, labmanager): ")
            if username is None: return False 
            password = self.get_input("Login", "Password(123): ")
            if password is None: return False
            
            if self.system.attempt_login(username, password):
                return True
            else:
                self.display_message("Error", "Invalid credentials.")

    
    def handle_patient_registration(self):
        name = self.get_input("Register Patient", "Patient Name: ")
        if not name: return
        email = self.get_input("Register Patient", "Patient Email: ")
        if not email: return
        try:
            patient = self.system.register_patient_logic(name, email)
            self.display_message("Success", f"Patient {patient.name} (ID: {patient.id}) created.")
            self._select_tests_for_patient(patient)
        except Exception as e:
            self.display_message("Error", str(e))

    def _select_tests_for_patient(self, patient: Patient):
        selected_tests: List[Test] = []
        added_test_ids = set() 
        
        while True:
            group_options = [g.group_name for g in self.system.test_groups.values()]
            group_choice_idx = self.navigate_menu_modal("Select Test Group", group_options + ["Done Selecting"])
            
            if group_choice_idx == -1 or group_choice_idx == len(group_options): break
            chosen_group = list(self.system.test_groups.values())[group_choice_idx]
            
            test_options = [f"{t.name} (Rs.{t.price:.2f})" for t in chosen_group.tests]
            current_group_tests_templates = chosen_group.tests
            
            selected_indices = self.navigate_multi_select_modal(f"Select from {chosen_group.group_name}", test_options)
            
            for idx in selected_indices:
                template = current_group_tests_templates[idx]
                if template.id not in added_test_ids: 
                    new_test_instance = Test(
                        id=f"{template.id}-{int(time.time() * 1000)}",
                        name=template.name,
                        price=template.price,
                        test_group_name=template.test_group_name,
                        specimen=template.specimen
                    )
                    selected_tests.append(new_test_instance)
                    added_test_ids.add(template.id)

        if not selected_tests:
            return self.display_message("Info", "No tests selected.")
        
        invoice = self.system.generate_invoice_logic(patient, selected_tests)
        self.display_message(f"Invoice {invoice.id}", invoice.get_display_format())

    def handle_manage_appointments(self):
        options = self.system.appointments + ["Add New Appointment", "Cancel"]
        choice_idx = self.navigate_menu_modal("Manage Appointments", options)
        if choice_idx == len(options) - 2:
            name = self.get_input("New Appointment", "Patient Name: ")
            if not name: return
            date = self.get_input("New Appointment", "Date (YYYY-MM-DD): ")
            time_val = self.get_input("New Appointment", "Time (HH:MM): ")
            if self.system.add_appointment(date, time_val, name):
                self.display_message("Success", "Appointment added.")
            else:
                self.display_message("Error", "Invalid date/time format.")

    def handle_view_all_patients(self):
        """View all registered patients"""
        if not self.system.patients:
            return self.display_message("Info", "No patients registered.")
        
        patient_list = list(self.system.patients.values())
        options = [f"{p.name} (ID: {p.id})" for p in patient_list] + ["Back"]
        choice_idx = self.navigate_menu_modal("All Patients", options)
        
        if choice_idx == -1 or choice_idx == len(options) - 1:
            return
        
        patient = patient_list[choice_idx]
        lines = [
            f"Patient: {patient.name}",
            f"ID: {patient.id}",
            f"Email: {patient.email}",
            f"Tests Ordered: {len(patient.tests_ordered)}",
            f"Invoices: {len(patient.invoices)}",
        ]
        self.display_message("Patient Details", "\n".join(lines))

    def handle_update_patient(self):
        """Update patient information"""
        patient_id = self.get_input("Update Patient", "Enter Patient ID: ")
        patient = self.system.get_patient_by_id(patient_id)
        if not patient:
            return self.display_message("Error", "Patient not found.")
        
        name = self.get_input("Update Patient", f"Patient Name [{patient.name}]: ")
        if not name:
            name = patient.name
        
        email = self.get_input("Update Patient", f"Patient Email [{patient.email}]: ")
        if not email:
            email = patient.email
        
        try:
            patient.name = name
            patient.email = email
            if self.system.db_operations.connection:
                self.system.db_operations.update_patient(patient_id, name, email)
            self.display_message("Success", f"Patient {name} updated successfully.")
        except Exception as e:
            self.display_message("Error", f"Failed to update patient: {str(e)}")

    def handle_delete_patient(self):
        """Delete patient and all related data"""
        if not self.system.logged_in_user.has_permission("manage_patients"):
            self.display_message("Access Denied", "You don't have permission to delete patients.")
            return
        
        patient_id = self.get_input("Delete Patient", "Enter Patient ID: ")
        patient = self.system.get_patient_by_id(patient_id)
        if not patient:
            return self.display_message("Error", "Patient not found.")
        
        confirm = self.get_input("Delete Patient", f"Delete patient {patient.name}? This will delete all invoices, tests, and reports. [y/N]: ")
        if confirm.lower() != 'y':
            return self.display_message("Cancelled", "Patient deletion cancelled.")
        
        try:
            if self.system.db_operations.connection:
                self.system.db_operations.delete_patient_cascade(patient_id)
            
            # Remove from system
            if patient_id in self.system.patients:
                del self.system.patients[patient_id]
            if patient_id in self.system.users:
                del self.system.users[patient_id]
            
            self.display_message("Success", f"Patient {patient.name} and all related data deleted successfully.")
        except Exception as e:
            self.display_message("Error", f"Failed to delete patient: {str(e)}")

    def handle_verify_id(self):
        patient_id = self.get_input("Verify ID", "Enter Patient ID: ")
        patient = self.system.get_patient_by_id(patient_id)
        if patient: self.display_message("ID Verified", f"Patient Found:\n{patient.display_info()}")
        else: self.display_message("Error", "Patient ID not found.")

    def handle_sample_submissions(self):
        pending_tests = self.system.get_tests_by_status("Pending")
        if not pending_tests: return self.display_message("Info", "No pending samples.")
        
        options = []
        for t in pending_tests:
            patient = self.system.get_patient_by_id(t.patient_id)
            p_name = patient.name if patient else "Unknown"
            options.append(f"{t.name} for {p_name}")
        options.append("Cancel")

        choice_idx = self.navigate_menu_modal("Submit Sample", options)
        if choice_idx != -1 and choice_idx != len(options) - 1:
            t = pending_tests[choice_idx]
            t.status = "In Progress"
            if self.system.db_operations.connection:
                try:
                    self.system.db_operations.save_test(
                        t.id, t.name, t.price, t.test_group_name, t.specimen.id,
                        t.status, t.result, t.patient_id, t.technician_id
                    )
                except Exception as e:
                    self.display_message("Error", f"Failed to persist sample: {e}")
                    return
            self.display_message("Success", "Sample submitted to lab.")

    def handle_view_metrics(self):
        metrics = self.system.get_business_metrics()
        lines = [f"Total Revenue:    Rs.{metrics.get('Total Revenue', 0.0):.2f}",
                 f"Total Expenses:   Rs.{metrics.get('Total Expenses', 0.0):.2f}",
                 f"Est. Profit:      Rs.{metrics.get('Profit', 0.0):.2f}", 
                 "---",
                 f"Total Patients:   {int(metrics.get('Total Patients', 0))}"]
        self.display_message("Business Metrics", "\n".join(lines))

    def handle_view_finances(self):
        lines = [f"{key}: Rs.{value:.2f}" for key, value in self.system.finances.items()]
        lines.append("---"); lines.append("Add Expense"); lines.append("Cancel")
        choice_idx = self.navigate_menu_modal("Finances", lines)
        if choice_idx == len(lines) - 2:
            desc = self.get_input("Add Expense", "Description: ")
            amount_str = self.get_input("Add Expense", "Amount: ")
            try:
                amount = float(amount_str)
                if "Total Expenses" not in self.system.finances: self.system.finances["Total Expenses"] = 0.0
                self.system.finances["Total Expenses"] += amount
                self.system.finances[f"Expense: {desc}"] = amount
                # Persist to DB if available
                if self.system.db_operations.connection:
                    self.system.db_operations.save_expense(datetime.date.today().isoformat(), amount, desc)
                self.display_message("Success", "Expense added.")
            except:
                self.display_message("Error", "Invalid amount.")

    def handle_view_compliance(self):
        options = self.system.compliance_reports + ["Add New Report", "Cancel"]
        choice_idx = self.navigate_menu_modal("Compliance", options)
        if choice_idx == len(options) - 2:
            report = self.get_input("New Report", "Report Summary: ")
            if report:
                report_entry = f"{datetime.date.today()} - {report}"
                self.system.compliance_reports.append(report_entry)
                if self.system.db_operations.connection:
                    self.system.db_operations.save_compliance_report(report, datetime.datetime.now().isoformat())
                self.display_message("Success", "Compliance report saved successfully.")

    def handle_view_operations_report(self):
        lines = [f"Total Patients: {len(self.system.patients)}",
                 f"Pending Tests: {len(self.system.get_tests_by_status('Pending'))}",
                 f"Completed Tests: {len(self.system.get_tests_by_status('Completed'))}"]
        self.display_message("Operations Report", "\n".join(lines))

    def handle_approve_results(self):
        tests = self.system.get_tests_by_status("Completed")
        if not tests: return self.display_message("Info", "No completed tests.")
        
        options = []
        for t in tests:
            patient = self.system.get_patient_by_id(t.patient_id)
            p_name = patient.name if patient else "Unknown"
            options.append(f"{t.name} for {p_name} (Res: {t.result})")
        options.append("Cancel")

        choice_idx = self.navigate_menu_modal("Approve Results", options)
        if choice_idx != -1 and choice_idx != len(options) - 1:
            t = tests[choice_idx]
            t.status = "Approved"
            if self.system.db_operations.connection:
                self.system.db_operations.save_test(
                    t.id, t.name, t.price, t.test_group_name, t.specimen.id,
                    t.status, t.result, t.patient_id, t.technician_id
                )
            patient = self.system.get_patient_by_id(t.patient_id)
            if patient:
                patient.messages.append(f"Result Ready: {t.name} - {t.result}")
            self.display_message("Success", f"{t.name} approved.")

    def handle_manage_inventory(self):
        items = list(self.system.inventory.keys())
        options = [f"{item}: {self.system.inventory[item]}" for item in items] + ["Add/Update Item", "Cancel"]
        choice_idx = self.navigate_menu_modal("Inventory", options)
        
        if choice_idx == len(options) - 2:
            item_name = self.get_input("Item", "Item Name: ")
            if not item_name: return
            qty_str = self.get_input("Item", "Quantity to Add: ")
            try:
                qty = int(qty_str)
                current_qty = self.system.inventory.get(item_name, 0)
                new_qty = current_qty + qty
                if self.system.db_operations.connection:
                    self.system.db_operations.save_inventory_item(item_name, new_qty)
                    # Reload from DB to ensure UI reflects actual DB state
                    self.system.inventory.clear()
                    for row in self.system.db_operations.get_all_inventory():
                        self.system.inventory[row['item_name']] = int(row['quantity'])
                else:
                    self.system.inventory[item_name] = new_qty # fallback if no DB
                self.display_message("Success", f"Updated {item_name}. New Total: {self.system.inventory.get(item_name, new_qty)}")
            except ValueError:
                self.display_message("Error", "Invalid quantity.")
            except Exception as e:
                self.display_message("Error", f"Failed to save inventory: {str(e)}")

    def handle_view_staff(self):
        lines = [f"{u.name} ({u.role})" for u in self.system.users.values()]
        self.display_message("Staff", "\n".join(lines))

    def handle_view_performance_reports(self):
        techs = [u for u in self.system.users.values() if u.role.lower() == "lab technician"]
        lines = ["Technician Performance:"]
        
        all_completed_tests = self.system.get_tests_by_status("Completed") + \
                              self.system.get_tests_by_status("Approved") + \
                              self.system.get_tests_by_status("Reviewed")

        for tech in techs:
            count = sum(1 for t in all_completed_tests if t.technician_id == tech.id)
            lines.append(f"{tech.name}: {count} tests performed.")
            
        self.display_message("Performance", "\n".join(lines))

    def handle_order_tests(self):
        pid = self.get_input("Order", "Patient ID: ")
        patient = self.system.get_patient_by_id(pid)
        if patient: self._select_tests_for_patient(patient)
        else: self.display_message("Error", "Not found.")

    def handle_review_results(self, doctor_id: str):
        tests = self.system.get_tests_by_status("Approved")
        if not tests: return self.display_message("Info", "No results to review.")
        
        options = [f"{t.name} (Pat: {t.patient_id})" for t in tests] + ["Cancel"]
        choice_idx = self.navigate_menu_modal("Review", options)
        if choice_idx != -1 and choice_idx != len(options) - 1:
            t = tests[choice_idx]
            opts = [f"Res: {t.result}", "Mark Reviewed", "Cancel"]
            act = self.navigate_menu_modal(f"Review {t.name}", opts)
            if act == 1:
                t.status = "Reviewed"
                if self.system.db_operations.connection:
                    self.system.db_operations.save_test(
                        t.id, t.name, t.price, t.test_group_name, t.specimen.id,
                        t.status, t.result, t.patient_id, t.technician_id
                    )
                self.display_message("Success", "Archived.")

    def handle_track_samples(self):
        pid = self.get_input("Track", "Patient ID: ")
        patient = self.system.get_patient_by_id(pid)
        if not patient: return self.display_message("Error", "Not found.")
        lines = [f"- {t.name}: {t.status}" for t in patient.tests_ordered]
        self.display_message("Status", "\n".join(lines) if lines else "No tests.")

    def handle_perform_tests(self):
        tests = self.system.get_tests_by_status("In Progress")
        if not tests: return self.display_message("Info", "No tests to run.")
        
        options = [f"{t.name} ({t.patient_id})" for t in tests] + ["Cancel"]
        choice_idx = self.navigate_menu_modal("Perform Test", options)
        if choice_idx != -1 and choice_idx != len(options) - 1:
            t = tests[choice_idx]
            res = self.get_input("Result", f"Enter result for {t.name}: ")
            if res is not None:
                t.status = "Completed"
                t.result = res
                t.technician_id = self.system.logged_in_user.id
                if self.system.db_operations.connection:
                    self.system.db_operations.save_test(
                        t.id, t.name, t.price, t.test_group_name, t.specimen.id,
                        t.status, t.result, t.patient_id, t.technician_id
                    )
                self.display_message("Success", "Test completed.")

    def handle_track_sample_flow(self):
        all_tests = []
        for p in self.system.patients.values():
            if p.tests_ordered: all_tests.extend(p.tests_ordered)
            
        if not all_tests: return self.display_message("Info", "No tests in system.")
        
        options = []
        for t in all_tests:
            try:
                options.append(f"{t.name} - {t.status}")
            except: pass
            
        self.navigate_menu_modal("Sample Flow", options)

    def handle_equipment_logs(self):
        options = self.system.equipment_logs + ["Add Log", "Cancel"]
        choice_idx = self.navigate_menu_modal("Equip Logs", options)
        if choice_idx == len(options) - 2:
            entry = self.get_input("Log", "Entry: ")
            if entry:
                log_entry = f"{datetime.date.today()} - {entry}"
                self.system.equipment_logs.append(log_entry)
                if self.system.db_operations.connection:
                    self.system.db_operations.save_equipment_log(entry, datetime.date.today().isoformat())

    def handle_see_patient_reports(self):
        pid = self.get_input("Report", "Patient ID: ")
        patient = self.system.get_patient_by_id(pid)
        if not patient: return self.display_message("Error", "Not found.")
        
        lines = [f"Report: {patient.name}", "="*20]
        for t in patient.tests_ordered:
            res = t.result if t.result else "N/A"
            lines.append(f"{t.name}: {t.status} | Res: {res}")
            
        self.display_message("Patient Report", "\n".join(lines))

    def handle_attendance_management(self):
        """Handle employee attendance tracking"""
        if not self.system.logged_in_user.has_permission("manage_attendance"):
            self.display_message("Access Denied", "You don't have permission to manage attendance.")
            return
        options = ["View Attendance", "Mark Attendance", "Clock In/Out", "Back"]
        choice_idx = self.navigate_menu_modal("Attendance Management", options)
        
        if choice_idx == 0:
            # View attendance
            emp_list = list(self.system.employees.keys())
            if not emp_list:
                return self.display_message("Info", "No employees found.")
            
            emp_options = [self.system.employees[e].name for e in emp_list] + ["Back"]
            emp_idx = self.navigate_menu_modal("Select Employee", emp_options)
            
            if emp_idx == -1 or emp_idx == len(emp_options) - 1:
                return
            
            emp_id = emp_list[emp_idx]
            emp = self.system.employees[emp_id]
            
            # Show attendance summary for current month
            today = datetime.date.today()
            summary = self.system.attendance.get_attendance_summary(emp_id, today.month, today.year)
            
            lines = [
                f"Attendance for {emp.name}",
                f"Month: {today.strftime('%B %Y')}",
                "─" * 40,
                f"Present Days:      {summary['total_present']}",
                f"Absent Days:       {summary['total_absent']}",
                f"Leave Days:        {summary['total_leave']}",
                f"Half Days:         {summary['total_half_day']}",
                f"Total Hours:       {summary['total_worked_hours']:.1f}",
                f"Avg Hours/Day:     {summary['average_hours_per_day']:.1f}",
            ]
            self.display_message(f"Attendance - {emp.name}", "\n".join(lines))
        
        elif choice_idx == 1:
            # Mark attendance
            emp_list = list(self.system.employees.keys())
            if not emp_list:
                return self.display_message("Info", "No employees found.")
            
            emp_options = [self.system.employees[e].name for e in emp_list] + ["Back"]
            emp_idx = self.navigate_menu_modal("Select Employee", emp_options)
            
            if emp_idx == -1 or emp_idx == len(emp_options) - 1:
                return
            
            emp_id = emp_list[emp_idx]
            status_options = ["Present", "Absent", "Leave", "Half-day"]
            status_idx = self.navigate_menu_modal("Select Status", status_options)
            
            if status_idx == -1:
                return
            
            status = status_options[status_idx]
            check_in = None
            check_out = None
            
            if status == "Present":
                check_in = datetime.time(9, 0)
                check_out = datetime.time(17, 30)
            
            record = AttendanceRecord(emp_id, datetime.date.today(), check_in, check_out, status)
            self.system.attendance.add_record(record)
            self.display_message("Success", f"Attendance marked for {self.system.employees[emp_id].name}")
        
        elif choice_idx == 2:
            # Clock In/Out
            emp_list = list(self.system.employees.keys())
            if not emp_list:
                return self.display_message("Info", "No employees found.")
            
            emp_options = [self.system.employees[e].name for e in emp_list] + ["Back"]
            emp_idx = self.navigate_menu_modal("Select Employee", emp_options)
            
            if emp_idx == -1 or emp_idx == len(emp_options) - 1:
                return
            
            emp_id = emp_list[emp_idx]
            action_options = ["Clock In", "Clock Out"]
            action_idx = self.navigate_menu_modal("Clock In/Out", action_options)
            
            if action_idx == -1:
                return
            
            today = datetime.date.today()
            now = datetime.datetime.now().time()
            
            # Find any existing record for this employee for today
            today_record = next((r for r in self.system.attendance.records if r.employee_id == emp_id and r.date == today), None)

            if action_idx == 0:
                # Clock In
                if not today_record:
                    today_record = AttendanceRecord(emp_id, today, check_in=now, check_out=None, status="Present")
                    # Use Attendance.add_record so it persists and deduplicates
                    self.system.attendance.add_record(today_record)
                else:
                    today_record.check_in = now
                    self.system.attendance.add_record(today_record)

                self.display_message("Success", f"Clocked in at {now.strftime('%H:%M')}")
            else:
                # Clock Out
                if not today_record:
                    self.display_message("Error", "Please clock in first.")
                    return

                today_record.check_out = now
                # Ensure worked hours and persistence via add_record
                self.system.attendance.add_record(today_record)
                self.display_message("Success", f"Clocked out at {now.strftime('%H:%M')}")

    def handle_payroll_management(self):
        """Handle payroll operations"""
        if not self.system.logged_in_user.has_permission("manage_payroll"):
            self.display_message("Access Denied", "You don't have permission to manage payroll.")
            return
        options = ["View Payroll", "Generate Payroll", "Approve Payroll", "Mark as Paid", "Back"]
        choice_idx = self.navigate_menu_modal("Payroll Management", options)
        
        if choice_idx == 0:
            # View payroll
            emp_list = list(self.system.employees.keys())
            if not emp_list:
                return self.display_message("Info", "No employees found.")
            
            emp_options = [self.system.employees[e].name for e in emp_list] + ["Back"]
            emp_idx = self.navigate_menu_modal("Select Employee", emp_options)
            
            if emp_idx == -1 or emp_idx == len(emp_options) - 1:
                return
            
            emp_id = emp_list[emp_idx]
            payroll_history = self.system.payroll.get_employee_payroll_history(emp_id)
            
            if not payroll_history:
                return self.display_message("Info", "No payroll records found.")
            
            # Show latest payroll record
            latest = payroll_history[-1]
            self.display_message("Payroll Record", latest.get_display_format())
        
        elif choice_idx == 1:
            # Generate payroll for current month
            emp_list = list(self.system.employees.keys())
            if not emp_list:
                return self.display_message("Info", "No employees found.")
            
            emp_options = [self.system.employees[e].name for e in emp_list] + ["All Employees", "Back"]
            emp_idx = self.navigate_menu_modal("Select Employee", emp_options)
            
            # If user cancelled or chose Back (last option), return
            if emp_idx == -1 or emp_idx == len(emp_options) - 1:
                return
            
            today = datetime.date.today()
            
            if emp_idx == len(emp_options) - 2:
                # Generate for all employees
                for emp_id in emp_list:
                    self.system.payroll.generate_payroll(emp_id, today.month, today.year, self.system.attendance)
                self.display_message("Success", f"Payroll generated for all employees for {today.strftime('%B %Y')}")
            else:
                emp_id = emp_list[emp_idx]
                payroll_record = self.system.payroll.generate_payroll(emp_id, today.month, today.year, self.system.attendance)
                self.display_message("Payroll Generated", payroll_record.get_display_format())
        
        elif choice_idx == 2:
            # Approve payroll
            emp_list = list(self.system.employees.keys())
            if not emp_list:
                return self.display_message("Info", "No employees found.")
            
            emp_options = [self.system.employees[e].name for e in emp_list] + ["Back"]
            emp_idx = self.navigate_menu_modal("Select Employee", emp_options)
            
            if emp_idx == -1 or emp_idx == len(emp_options) - 1:
                return
            
            emp_id = emp_list[emp_idx]
            today = datetime.date.today()
            
            # Find draft payroll record
            draft_records = [r for r in self.system.payroll.records 
                           if r.employee_id == emp_id and r.period_month == today.month 
                           and r.period_year == today.year and r.status == "Draft"]
            
            if not draft_records:
                return self.display_message("Info", "No draft payroll record found for approval.")
            
            record = draft_records[0]
            confirm = self.get_input(f"Approve payroll for {record.employee_name}? (Rs. {record.net_salary:,.2f}) [y/N]: ")
            if confirm.lower() == 'y':
                record.approve_payroll(self.system.logged_in_user.id)
                if self.system.db_operations.connection:
                    self.system.payroll.persist_record(record)
                self.display_message("Success", "Payroll approved successfully.")
        
        elif choice_idx == 3:
            # Mark as paid
            emp_list = list(self.system.employees.keys())
            if not emp_list:
                return self.display_message("Info", "No employees found.")
            
            emp_options = [self.system.employees[e].name for e in emp_list] + ["Back"]
            emp_idx = self.navigate_menu_modal("Select Employee", emp_options)
            
            if emp_idx == -1 or emp_idx == len(emp_options) - 1:
                return
            
            emp_id = emp_list[emp_idx]
            today = datetime.date.today()
            
            # Find approved payroll record
            approved_records = [r for r in self.system.payroll.records 
                              if r.employee_id == emp_id and r.period_month == today.month 
                              and r.period_year == today.year and r.status == "Approved"]
            
            if not approved_records:
                return self.display_message("Info", "No approved payroll record found.")
            
            record = approved_records[0]
            confirm = self.get_input(f"Mark payroll as paid for {record.employee_name}? [y/N]: ")
            if confirm.lower() == 'y':
                record.mark_as_paid()
                if self.system.db_operations.connection:
                    self.system.payroll.persist_record(record)
                self.display_message("Success", "Payroll marked as paid.")

    def handle_leave_management(self):
        """Handle leave management operations"""
        if not self.system.logged_in_user.has_permission("manage_leave"):
            self.display_message("Access Denied", "You don't have permission to manage leave.")
            return
        options = ["View Leave Requests", "Approve/Reject Leave", "View Leave Balances", "Back"]
        choice_idx = self.navigate_menu_modal("Leave Management", options)
        
        if choice_idx == 0:
            # View leave requests
            requests = self.system.leave_manager.get_pending_requests()
            if not requests:
                return self.display_message("Info", "No pending leave requests.")
            
            request_lines = []
            for req in requests:
                emp = self.system.employees.get(req.employee_id)
                emp_name = emp.name if emp else "Unknown"
                request_lines.append(f"{emp_name}: {req.start_date} to {req.end_date} ({req.status})")
            
            self.display_message("Pending Leave Requests", "\n".join(request_lines))
        
        elif choice_idx == 1:
            # Approve/Reject leave
            requests = self.system.leave_manager.get_pending_requests()
            if not requests:
                return self.display_message("Info", "No pending leave requests.")
            
            request_options = []
            for req in requests:
                emp = self.system.employees.get(req.employee_id)
                emp_name = emp.name if emp else "Unknown"
                request_options.append(f"{emp_name}: {req.start_date} to {req.end_date}")
            request_options.append("Back")
            
            req_idx = self.navigate_menu_modal("Select Request", request_options)
            if req_idx == -1 or req_idx == len(request_options) - 1:
                return
            
            req = requests[req_idx]
            action_options = ["Approve", "Reject"]
            action_idx = self.navigate_menu_modal("Action", action_options)
            
            if action_idx == -1:
                return
            
            if action_idx == 0:
                self.system.leave_manager.approve_leave(req.id, self.system.logged_in_user.id)
                self.display_message("Success", "Leave request approved.")
            else:
                self.system.leave_manager.reject_leave(req.id, self.system.logged_in_user.id)
                self.display_message("Success", "Leave request rejected.")
        
        elif choice_idx == 2:
            # View leave balances
            emp_list = list(self.system.employees.keys())
            if not emp_list:
                return self.display_message("Info", "No employees found.")
            
            emp_options = [self.system.employees[e].name for e in emp_list] + ["Back"]
            emp_idx = self.navigate_menu_modal("Select Employee", emp_options)
            
            if emp_idx == -1 or emp_idx == len(emp_options) - 1:
                return
            
            emp_id = emp_list[emp_idx]
            balance = self.system.leave_manager.get_leave_balance(emp_id)
            if balance:
                lines = [
                    f"Leave Balance for {self.system.employees[emp_id].name}",
                    f"Annual Leave: {balance.annual_leave} days",
                    f"Sick Leave: {balance.sick_leave} days",
                    f"Used Annual: {balance.used_annual_leave} days",
                    f"Used Sick: {balance.used_sick_leave} days"
                ]
                self.display_message("Leave Balance", "\n".join(lines))
            else:
                self.display_message("Info", "No leave balance found.")

    def handle_request_leave(self):
        """Handle employee leave request"""
        emp_id = self.system.logged_in_user.id
        
        # Get leave types
        leave_types = self.system.leave_manager.get_leave_types()
        if not leave_types:
            return self.display_message("Error", "No leave types configured.")
        
        type_options = [f"{lt.type_name} ({lt.max_days_per_year} days/year)" for lt in leave_types.values()]
        type_idx = self.navigate_menu_modal("Select Leave Type", type_options)
        
        if type_idx == -1:
            return
        
        leave_type_id = list(leave_types.keys())[type_idx]
        
        # Get dates
        start_date_str = self.get_input("Start Date (YYYY-MM-DD): ")
        if not start_date_str:
            return
        
        try:
            start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            return self.display_message("Error", "Invalid date format.")
        
        end_date_str = self.get_input("End Date (YYYY-MM-DD): ")
        if not end_date_str:
            return
        
        try:
            end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            return self.display_message("Error", "Invalid date format.")
        
        if end_date < start_date:
            return self.display_message("Error", "End date must be after start date.")
        
        reason = self.get_input("Reason for leave: ")
        if not reason:
            return
        
        # Create leave request
        request = LeaveRequest(0, emp_id, leave_type_id, start_date, end_date, reason, "Pending")
        success = self.system.leave_manager.request_leave(request)
        
        if success:
            self.display_message("Success", "Leave request submitted successfully.")
        else:
            self.display_message("Error", "Failed to submit leave request.")

    def handle_view_metrics_with_charts(self):
        """Display business metrics with ASCII charts"""
        metrics = self.system.get_business_metrics()
        
        # Create chart data
        revenue_data = {"Total Revenue": metrics.get('Total Revenue', 0.0),
                       "Expenses": metrics.get('Total Expenses', 0.0),
                       "Profit": metrics.get('Profit', 0.0)}
        
        chart = ChartRenderer.create_bar_chart("Business Metrics", revenue_data, width=30)
        self.display_message("Business Metrics", chart)

    def handle_view_dashboard_charts(self):
        """Display dashboard with charts"""
        if self.system.logged_in_user.__class__.__name__ not in ['Admin', 'Owner']:
            return
        
        # Chart 1: Revenue by Day
        if self.system.daily_revenue_history:
            revenue_values = list(self.system.daily_revenue_history.values())[-15:]
            chart1 = ChartRenderer.create_line_chart("Revenue Trend (Last 15 Days)", revenue_values, width=35)
        else:
            chart1 = "Revenue Trend: No data available"
        
        # Chart 2: Inventory Status
        inventory_data = self.system.inventory.copy()
        chart2 = ChartRenderer.create_bar_chart("Inventory Status", inventory_data, width=25, height=5)
        
        # Chart 3: Test Status Distribution
        test_status = {
            "Pending": len(self.system.get_tests_by_status("Pending")),
            "In Progress": len(self.system.get_tests_by_status("In Progress")),
            "Completed": len(self.system.get_tests_by_status("Completed")),
            "Approved": len(self.system.get_tests_by_status("Approved"))
        }
        chart3 = ChartRenderer.create_pie_chart("Test Status Distribution", test_status)
        
        combined = f"{chart1}\n\n{chart2}\n\n{chart3}"
        self.display_message("Dashboard Charts", combined)

    def handle_custom_reports(self):
        """Handle custom report generation"""
        if not self.system.logged_in_user.has_permission("generate_reports"):
            self.display_message("Access Denied", "You don't have permission to generate reports.")
            return
        
        report_options = ["Employee Summary", "Financial Summary", "Test Performance", "Real-time Analytics", "Back"]
        choice_idx = self.navigate_menu_modal("Custom Reports", report_options)
        
        if choice_idx == 0:
            # Employee Summary
            report = self.system.generate_custom_report("employee_summary")
            self.display_message("Employee Summary Report", report)
        
        elif choice_idx == 1:
            # Financial Summary
            report = self.system.generate_custom_report("financial_summary")
            self.display_message("Financial Summary Report", report)
        
        elif choice_idx == 2:
            # Test Performance
            report = self.system.generate_custom_report("test_performance")
            self.display_message("Test Performance Report", report)
        
        elif choice_idx == 3:
            # Real-time Analytics
            analytics = self.system.get_real_time_analytics()
            lines = ["REAL-TIME ANALYTICS", "=" * 50]
            
            # Revenue
            rev = analytics.get('revenue', {})
            lines.append(f"Monthly Revenue: Rs. {rev.get('monthly_total', 0):,.2f}")
            lines.append(f"Daily Average: Rs. {rev.get('daily_average', 0):,.2f}")
            lines.append(f"Growth Rate: {rev.get('growth_rate', 0):.1f}%")
            
            # Tests
            tests = analytics.get('tests', {})
            lines.append(f"Total Tests: {tests.get('total', 0)}")
            lines.append(f"Completion Rate: {tests.get('completion_rate', 0):.1f}%")
            
            # Employees
            emp = analytics.get('employees', {})
            lines.append(f"Active Employees: {emp.get('active', 0)}/{emp.get('total', 0)}")
            lines.append(f"Utilization Rate: {emp.get('utilization_rate', 0):.1f}%")
            
            # Leave
            leave = analytics.get('leave', {})
            lines.append(f"Pending Leave Requests: {leave.get('pending_requests', 0)}")
            
            self.display_message("Real-time Analytics", "\n".join(lines))

    def handle_help(self):
        """Display help and keyboard shortcuts"""
        help_text = """
ILMS HELP & KEYBOARD SHORTCUTS
===============================

NAVIGATION:
• ↑/↓ Arrow Keys: Navigate menu
• Enter/Space: Select option
• Q: Quit application
• D: Quick Dashboard access
• L: Quick Logout

MENU OPTIONS:
• DASHBOARD: View system overview
• Patient Management: Register patients, view reports
• Test Management: Order, review, approve tests
• Staff Management: View staff, performance reports
• Inventory & Equipment: Manage supplies and logs
• Financial Management: View metrics, finances
• Attendance & Payroll: Track time and salaries
• Leave Management: Request/approve leave
• Analytics: Charts, reports, real-time data

COLOR CODES:
• White: Normal text
• Cyan: Headers and accents
• Green: Success messages
• Red: Error messages
• Yellow: Warnings
• Blue: Information

TIPS:
• Use arrow keys for efficient navigation
• Press Q anytime to exit
• Dashboard (D) shows quick system overview
• All financial data is encrypted and secure
        """
        self.display_message("Help & Shortcuts", help_text.strip())

    def handle_profile_update(self, user: User):
        """Handle user profile update"""
        lines = [
            f"Current Profile",
            f"Name: {user.name}",
            f"Email: {user.email}",
            f"Role: {user.role}",
            f"ID: {user.id}",
        ]
        self.display_message("Profile", "\n".join(lines))
        
        options = ["Update Name", "Update Email", "Change Password", "Cancel"]
        choice_idx = self.navigate_menu_modal("Profile Options", options)
        
        if choice_idx == -1 or choice_idx == 3:
            return
        
        if choice_idx == 0:
            # Update name
            new_name = self.get_input("Update Profile", f"New Name [{user.name}]: ")
            if new_name:
                user.name = new_name
                if self.system.db_operations.connection:
                    self.system.db_operations.update_user(user.id, new_name, user.email)
                self.display_message("Success", f"Name updated to {new_name}")
        
        elif choice_idx == 1:
            # Update email
            new_email = self.get_input("Update Profile", f"New Email [{user.email}]: ")
            if new_email:
                user.email = new_email
                if self.system.db_operations.connection:
                    self.system.db_operations.update_user(user.id, user.name, new_email)
                self.display_message("Success", f"Email updated to {new_email}")
        
        elif choice_idx == 2:
            # Change password
            old_password = self.get_input("Change Password", "Current Password: ")
            if not old_password:
                return self.display_message("Cancelled", "Password change cancelled.")
            
            # Verify old password
            if not verify_password(old_password, user.password_salt, user.password_hash):
                return self.display_message("Error", "Current password is incorrect.")
            
            new_password = self.get_input("Change Password", "New Password: ")
            if not new_password:
                return self.display_message("Cancelled", "Password change cancelled.")
            
            # Hash new password
            new_salt, new_hash = hash_password(new_password)
            user.password_salt = new_salt
            user.password_hash = new_hash
            
            if self.system.db_operations.connection:
                self.system.db_operations.update_user(user.id, user.name, user.email, new_hash, new_salt)
            self.display_message("Success", "Password changed successfully.")

def main(stdscr):
    system = ILMSSystem()
    ui = ConsoleUI(system)
    ui.run(stdscr)

if __name__ == "__main__":
    try:
        os.system('cls' if os.name == 'nt' else 'clear')
        curses.wrapper(main)
    except Exception as e:
        print(f"Critical Error: {e}")
        import traceback
        traceback.print_exc()