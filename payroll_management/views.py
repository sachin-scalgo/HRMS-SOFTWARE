from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
from django.core.mail import EmailMessage
from company.models import Companies, MonthlyEffectiveDays
from employee.models import Employees, EmployeeLeaveBank
from payroll_management.models import EmployeeSalaryComponents
from leave_management.models import LeaveApplications
from employee.serializer import EmployeeSalaryComponentSerializer
from .models import EmployeeMonthlyPayrollData
from .serializer import (
    EmployeePayrollSerializer,
    EmployeeMonthlyPayrollSerializer,
    PayslipSerializer,
)
from leave_management.models import LeaveApplications
from .models import EmployeePayroll
from django.db import transaction
from django.db.models import Q, Sum
from decimal import Decimal
from employee.pagination import CustomPageNumberPagination
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from django.http import FileResponse
import calendar
from openpyxl import Workbook
from django.http import HttpResponse


# Create your views here.


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def CreatePayroll(request):
    data = request.data.copy()
    company = data.get("company")
    month = int(data.get("month", datetime.now().month))
    year = int(data.get("year", datetime.now().year))

    try:
        company = Companies.objects.get(id=company)
    except Companies.DoesNotExist:
        return Response(
            {"error": "Company not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    salary_components = EmployeeSalaryComponents.objects.filter(company=company)

    if not salary_components.exists():
        return Response(
            {"message": "No salary components found for this company."},
            status=status.HTTP_404_NOT_FOUND,
        )

    payrolls = EmployeePayroll.objects.filter(company=company, month=month, year=year)
    if not payrolls.exists():
        return Response(
            {"message": "No gross salary added."},
            status=status.HTTP_404_NOT_FOUND,
        )
    payroll_records = []
    updated_count, created_count = 0, 0
    effective_days = MonthlyEffectiveDays.objects.get(
        company=company, month=month, year=year
    )
    for payroll in payrolls:
        employee = payroll.employee
        gross_salary_amount = payroll.gross_salary

        lop_data = LeaveApplications.objects.filter(
            Q(from_date__month=month, from_date__year=year)
            | Q(to_date__month=month, to_date__year=year),
            company=company,
            employee=employee,
            leave_type_id=8,
        ).aggregate(total_lop_days=Sum("leave_days_taken"))

        lop_days = lop_data["total_lop_days"] or 0
        paid_days = effective_days.effective_days - lop_days

        if lop_days > 0:
            salary_per_day = gross_salary_amount / Decimal(30)
            lop_deduction = salary_per_day * Decimal(lop_days)
            gross_salary_amount = gross_salary_amount - lop_deduction

        basic = gross_salary_amount * Decimal("0.40")
        da = gross_salary_amount * Decimal("0.10")
        hra = Decimal("0.40") * (basic + da)

        pf = Decimal("0.12") * (basic + da)
        esi = Decimal("0.0075") * (basic + da)

        conveyance_allowance = Decimal("1600.00")
        medical_allowance = Decimal("1250.00")

        special_allowance = gross_salary_amount - (
            basic + da + hra + conveyance_allowance + medical_allowance
        )

        total_earnings = (
            basic
            + da
            + hra
            + conveyance_allowance
            + medical_allowance
            + special_allowance
        )
        total_deductions = pf + esi
        net_salary = total_earnings - total_deductions

        existing_payroll_for_current_month = EmployeeMonthlyPayrollData.objects.filter(
            employee=employee, company=company, month=month, year=year
        ).first()

        if existing_payroll_for_current_month:
            existing_payroll_for_current_month.gross_salary = gross_salary_amount
            existing_payroll_for_current_month.basic_pay = basic
            existing_payroll_for_current_month.hra = hra
            existing_payroll_for_current_month.da = da
            existing_payroll_for_current_month.ca = conveyance_allowance
            existing_payroll_for_current_month.ma = medical_allowance
            existing_payroll_for_current_month.sa = special_allowance
            existing_payroll_for_current_month.pf = pf
            existing_payroll_for_current_month.esi = esi
            existing_payroll_for_current_month.net_pay = net_salary
            existing_payroll_for_current_month.total_working_days = (
                effective_days.effective_days
            )
            existing_payroll_for_current_month.lop_days = lop_days
            existing_payroll_for_current_month.paid_days = paid_days
            existing_payroll_for_current_month.save()
            updated_count += 1
        else:
            payroll_records.append(
                EmployeeMonthlyPayrollData(
                    employee=employee,
                    company=company,
                    month=month,
                    year=year,
                    gross_salary=gross_salary_amount,
                    basic_pay=basic,
                    hra=hra,
                    da=da,
                    ca=conveyance_allowance,
                    ma=medical_allowance,
                    sa=special_allowance,
                    pf=pf,
                    esi=esi,
                    net_pay=net_salary,
                    total_working_days=effective_days.effective_days,
                    lop_days=lop_days,
                    paid_days=paid_days,
                )
            )
            created_count += 1

    if payroll_records:
        EmployeeMonthlyPayrollData.objects.bulk_create(payroll_records)

    return Response(
        {
            "message": "Payroll generated for current month",
            "created_records": created_count,
            "updated_records": updated_count,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ListPayrollData(request):
    company = request.query_params.get("company")
    month = request.query_params.get("month")
    year = request.query_params.get("year")

    if not company:
        return Response(
            {"error": "Company is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        company = Companies.objects.get(id=company)
    except Companies.DoesNotExist:
        return Response(
            {"error": "Company not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        monthly_payroll_data = EmployeeMonthlyPayrollData.objects.filter(
            company=company
        )

        if month:
            monthly_payroll_data = monthly_payroll_data.filter(month=month)
        if year:
            monthly_payroll_data = monthly_payroll_data.filter(year=year)

        monthly_payroll_data = monthly_payroll_data.select_related(
            "employee", "company"
        ).order_by("-year", "-month", "-id")

        paginator = CustomPageNumberPagination()
        paginated_qs = paginator.paginate_queryset(monthly_payroll_data, request)
        serializer = EmployeeMonthlyPayrollSerializer(paginated_qs, many=True)

        return paginator.get_paginated_response(serializer.data)

    except Exception as e:
        return Response(
            {"error": f"Failed to fetch payroll data: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ViewPayslip(request):
    company = request.query_params.get("company")
    employee = request.query_params.get("employee")
    month = request.query_params.get("month")
    year = request.query_params.get("year")

    if not all([company, employee, month, year]):
        return Response(
            {"error": "company, employee, month, and year are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payroll = EmployeeMonthlyPayrollData.objects.select_related(
            "employee", "company"
        ).get(company=company, employee=employee, month=month, year=year)
    except EmployeeMonthlyPayrollData.DoesNotExist:
        return Response(
            {"error": "Payslip not found for the given employee and period."},
            status=status.HTTP_404_NOT_FOUND,
        )

    payslip_serializer = PayslipSerializer(payroll).data
    payslip_serializer["paid_days"] = float(payslip_serializer.get("paid_days", 0))
    payslip_serializer["lop_days"] = float(payslip_serializer.get("lop_days", 0))
    return Response(payslip_serializer, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def DownloadPayslip(request):
    company = request.query_params.get("company")
    employee = request.query_params.get("employee")
    month = request.query_params.get("month")
    year = request.query_params.get("year")

    if not all([company, employee, month, year]):
        return Response(
            {"error": "company, employee, month, and year are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payroll = EmployeeMonthlyPayrollData.objects.select_related(
            "employee", "company", "employee__employee_details__designation"
        ).get(company=company, employee=employee, month=month, year=year)
    except EmployeeMonthlyPayrollData.DoesNotExist:
        return Response(
            {"error": "Payslip not found for the given employee and period."},
            status=status.HTTP_404_NOT_FOUND,
        )

    lop_data = LeaveApplications.objects.filter(
        Q(from_date__month=month, from_date__year=year)
        | Q(to_date__month=month, to_date__year=year),
        company=company,
        employee=employee,
        leave_type_id=8,
    ).aggregate(total_lop_days=Sum("leave_days_taken"))
    lop_days = lop_data["total_lop_days"] or 0

    total_days_in_month = calendar.monthrange(int(year), int(month))[1]
    paid_days = total_days_in_month - lop_days

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)

    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, 800, f"PAYSLIP - {month}/{year}")
    p.setFont("Helvetica", 11)
    p.drawString(50, 770, f"{payroll.company.name}")

    y = 740
    details = [
        ("Emp ID", payroll.employee.employee_internal_id),
        (
            "Employee Name",
            f"{payroll.employee.first_name} {payroll.employee.last_name}".strip(),
        ),
        ("Designation", payroll.employee.employee_details.designation.name),
        ("Bank A/C", payroll.employee.employee_details.bank_account_number or " "),
        ("Paid Days", float(paid_days)),
        ("LOP", float(lop_days)),
    ]

    for label, value in details:
        p.drawString(50, y, f"{label}: {value}")
        y -= 20

    y -= 10
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Earnings")
    p.drawString(300, y, "Deductions")
    y -= 20
    p.setFont("Helvetica", 11)

    earnings = [
        ("Basic", payroll.basic_pay),
        ("DA", payroll.da),
        ("HRA", payroll.hra),
        ("Conveyance", payroll.ca),
        ("Medical", payroll.ma),
        ("Special", payroll.sa),
    ]
    deductions = [
        ("PF", payroll.pf),
        ("ESI", payroll.esi),
    ]

    for i in range(max(len(earnings), len(deductions))):
        if i < len(earnings):
            p.drawString(50, y, f"{earnings[i][0]}")
            p.drawRightString(220, y, f"{earnings[i][1]:.2f}")
        if i < len(deductions):
            p.drawString(300, y, f"{deductions[i][0]}")
            p.drawRightString(420, y, f"{deductions[i][1]:.2f}")
        y -= 20

    y -= 10
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y, f"Gross Pay: {payroll.gross_salary:.2f}")
    p.drawString(300, y, f"Net Pay: {payroll.net_pay:.2f}")

    p.showPage()
    p.save()

    buffer.seek(0)
    filename = f"Payslip_{payroll.employee.first_name}_{month}_{year}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ExportMonthlyPayroll(request):
    company = request.query_params.get("company")
    month = request.query_params.get("month")
    year = request.query_params.get("year")

    if not all([company, month, year]):
        return Response(
            {"error": "company, month, and year parameters are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        company_obj = Companies.objects.get(id=company)
    except Companies.DoesNotExist:
        return Response(
            {"error": "Company not found."}, status=status.HTTP_404_NOT_FOUND
        )

    payroll_data = EmployeeMonthlyPayrollData.objects.select_related(
        "employee", "employee__employee_details"
    ).filter(company=company_obj, month=month, year=year)

    if not payroll_data.exists():
        return Response(
            {"message": "No payroll records found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    wb = Workbook()
    ws = wb.active
    month_name = calendar.month_name[int(month)]
    ws.title = f"Payroll_{month_name}_{year}"

    headers = [
        "Sl.No",
        "Employee Name",
        "Account Number",
        "Account Type",
        "Net Pay Amount",
    ]
    ws.append(headers)

    total_net_pay = Decimal("0.00")
    row_number = 1

    for record in payroll_data:
        employee = record.employee
        details = employee.employee_details

        row_number += 1
        net_pay = record.net_pay or Decimal(0)
        total_net_pay += net_pay

        ws.append(
            [
                row_number - 1,
                f"{employee.first_name} {employee.last_name}".strip(),
                details.bank_account_number if details else "N/A",
                details.bank_account_type if details else "N/A",
                f"{net_pay:.2f}",
            ]
        )

    ws.append(["", "", "", "Total Net Pay", f"{total_net_pay:.2f}"])

    filename = f"Payroll_{company_obj.name}_{month}_{year}.xlsx"

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    wb.save(response)
    return response
