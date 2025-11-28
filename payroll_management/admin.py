from django.contrib import admin
from payroll_management.models import EmployeeSalaryComponents


@admin.register(EmployeeSalaryComponents)
class EmployeeSalaryComponentsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "employee",
        "company",
        "component",
        "amount",
        "created_at",
        "updated_at",
    )
    list_filter = ("company", "component")
    search_fields = ("employee__first_name", "employee__last_name", "component__name")
