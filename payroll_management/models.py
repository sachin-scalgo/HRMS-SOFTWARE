from django.db import models
from employee.models import Employees
from company.models import SalaryComponents


# Create your models here.
class EmployeeSalaryComponents(models.Model):
    employee = models.ForeignKey(Employees, on_delete=models.RESTRICT)
    company = models.ForeignKey(
        "company.Companies", on_delete=models.CASCADE, null=True, blank=True
    )
    component = models.ForeignKey(
        SalaryComponents,
        on_delete=models.RESTRICT,
        related_name="component",
        null=True,
        blank=True,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "employee_salary_components"
        unique_together = ("employee", "component")


class EmployeePayroll(models.Model):
    employee = models.ForeignKey("employee.Employees", on_delete=models.CASCADE)
    company = models.ForeignKey("company.Companies", on_delete=models.CASCADE)
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2)
    total_deductions = models.DecimalField(max_digits=10, decimal_places=2)
    net_pay = models.DecimalField(max_digits=10, decimal_places=2)
    month = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "employee_payroll"
        unique_together = ("employee", "month", "year")
        verbose_name = "Employee Payroll"
        verbose_name_plural = "Employee Payrolls"

    def __str__(self):
        return f"{self.employee} - {self.month}/{self.year}"


class EmployeeMonthlyPayrollData(models.Model):
    employee = models.ForeignKey("employee.Employees", on_delete=models.CASCADE)
    company = models.ForeignKey("company.Companies", on_delete=models.CASCADE)
    month = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()
    total_working_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    lop_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    paid_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    basic_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hra = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    da = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ca = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ma = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sa = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pf = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    esi = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "employee_monthly_payroll"
        unique_together = ("employee", "company", "month", "year")
