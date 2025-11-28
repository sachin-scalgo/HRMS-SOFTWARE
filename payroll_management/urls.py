from django.urls import path
from .views import (
    CreatePayroll,
    ListPayrollData,
    ExportMonthlyPayroll,
    ViewPayslip,
    DownloadPayslip,
)

urlpatterns = [
    path("generate", CreatePayroll, name="generate-payroll"),
    path("list", ListPayrollData, name="list-payroll"),
    path("export-payroll", ExportMonthlyPayroll, name="export-payroll"),
    path("view-payslip", ViewPayslip, name="view-payslip"),
    path("download-payslip", DownloadPayslip, name="download-payslip"),
]
