from rest_framework import serializers
from payroll_management.models import EmployeePayroll, EmployeeMonthlyPayrollData
from django.db.models import Sum, Q
import calendar


class EmployeePayrollSerializer(serializers.ModelSerializer):
    employee = serializers.CharField(source="employee.first_name", read_only=True)
    company = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = EmployeePayroll
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]

    def to_representation(self, instance):
        """
        Convert Decimal fields to float for cleaner frontend usage.
        """
        data = super().to_representation(instance)
        for field in ["gross_salary", "total_earnings", "total_deductions", "net_pay"]:
            if data.get(field) is not None:
                data[field] = float(data[field])
        return data


class EmployeeMonthlyPayrollSerializer(serializers.ModelSerializer):
    employee_first_name = serializers.CharField(
        source="employee.first_name", read_only=True
    )
    employee_last_name = serializers.CharField(
        source="employee.last_name", read_only=True
    )
    employee_email = serializers.CharField(source="employee.email", read_only=True)
    employee_internal_id = serializers.CharField(
        source="employee.employee_internal_id", read_only=True
    )
    date_of_joining = serializers.CharField(
        source="employee.date_of_joining", read_only=True
    )
    employee_designation = serializers.CharField(
        source="employee.employee_details.designation.name", read_only=True
    )

    class Meta:
        model = EmployeeMonthlyPayrollData
        fields = [
            "id",
            "employee",
            "employee_first_name",
            "employee_last_name",
            "employee_internal_id",
            "employee_designation",
            "date_of_joining",
            "employee_email",
            "month",
            "year",
            "gross_salary",
            "basic_pay",
            "hra",
            "da",
            "ca",
            "ma",
            "sa",
            "pf",
            "esi",
            "net_pay",
            "total_working_days",
            "lop_days",
            "paid_days",
            "created_at",
        ]


class PayslipSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_internal_id = serializers.CharField(
        source="employee.employee_internal_id", read_only=True
    )
    company_name = serializers.CharField(source="company.name", read_only=True)
    designation = serializers.CharField(
        source="employee.employee_details.designation.title", read_only=True
    )
    account_number = serializers.CharField(
        source="employee.bank_account_number", read_only=True
    )
    designation = serializers.CharField(
        source="employee.employee_details.designation.name", read_only=True
    )
    lop_days = serializers.SerializerMethodField()
    paid_days = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeMonthlyPayrollData
        fields = [
            "employee_name",
            "employee_internal_id",
            "designation",
            "month",
            "year",
            "gross_salary",
            "basic_pay",
            "hra",
            "da",
            "ca",
            "ma",
            "sa",
            "pf",
            "esi",
            "net_pay",
            "account_number",
            "company_name",
            "lop_days",
            "paid_days",
        ]

    def get_employee_name(self, obj):
        """Combine first_name and last_name safely."""
        first = obj.employee.first_name or ""
        last = obj.employee.last_name or ""
        return f"{first} {last}".strip()

    def get_lop_days(self, obj):
        from leave_management.models import LeaveApplications

        month = obj.month
        year = obj.year
        employee = obj.employee
        company = obj.company

        lop_data = LeaveApplications.objects.filter(
            Q(from_date__month=month, from_date__year=year)
            | Q(to_date__month=month, to_date__year=year),
            company=company,
            employee=employee,
            leave_type_id=8,
        ).aggregate(total_lop=Sum("leave_days_taken"))

        return lop_data["total_lop"] or 0

    def get_paid_days(self, obj):
        total_days = calendar.monthrange(obj.year, obj.month)[1]
        lop_days = self.get_lop_days(obj)
        return total_days - lop_days
