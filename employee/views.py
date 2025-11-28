from django.contrib.auth import authenticate
from django.shortcuts import render
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db import transaction
from rest_framework import status
from company.models import Companies, LeaveTypes, SalaryComponents
from employee.serializer import EmployeeSalaryComponentSerializer
from employee.models import Employees, EmployeeLeaveBank, EmployeeDetails
from payroll_management.models import EmployeeSalaryComponents, EmployeePayroll
from .serializer import (
    EmployeeSerializer,
    LeaveBankSerializer,
)
from payroll_management.serializer import EmployeePayrollSerializer
from company.serializer import SalaryComponentsSerializer, CompanySerializer
from .pagination import CustomPageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.utils import timezone


# Create your views here.


def login_page(request):
    return render(request, "login.html")


def RenderEmployee(request):
    return render(request, "employee_list.html")


@api_view(["POST"])
def login(request):
    data = request.data.copy()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return Response(
            {"error": "Email and password required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    employee = authenticate(email=email, password=password)

    if employee is None:
        return Response(
            {"error": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED
        )

    if not employee.is_active:
        return Response(
            {"error": "Account is inactive. Please contact support team."},
            status=status.HTTP_403_FORBIDDEN,
        )

    role = "employee"
    try:
        company = Companies.objects.get(admin_user_id=employee.id)
        if employee.is_superuser:
            role = "admin"
    except Companies.DoesNotExist:
        pass

    refresh = RefreshToken.for_user(employee)
    refresh["role"] = role
    refresh["email"] = employee.email

    is_reporting_head = False
    if role == "employee":
        is_reporting_head = EmployeeDetails.objects.filter(
            reporting_manager_id=employee.id
        ).exists()

    company = Companies.objects.get(id=employee.company_id)
    company_data = CompanySerializer(company).data

    response_data = {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "id": employee.id,
        "username": employee.username,
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "role": role,
        "company": employee.company_id,
        "company_details": company_data,
        "is_reporting_head": is_reporting_head,
    }

    return Response(
        {"data": response_data, "message": "Logined Successfully."},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])  # ← GET method for profile retrieval
@permission_classes([IsAuthenticated])
def GetProfile(request):
    user = request.user
    company = Companies.objects.get(id=user.company_id)
    company_data = CompanySerializer(company).data

    return Response(
        {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "company": user.company_id,
            "admin": user.is_superuser,
            "company_details": company_data,
        }
    )


@api_view(["POST"])
def logout(request):
    try:
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"error": "Refresh token not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = RefreshToken(refresh_token)
        token.blacklist()

        return Response(
            {"message": "Logged out successfully."}, status=status.HTTP_200_OK
        )
    except Exception:
        return Response(
            {"error": "Invalid token."},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def CreateEmployee(request):
    data = request.data.copy()
    employee_serializer = EmployeeSerializer(data=data)

    try:
        if employee_serializer.is_valid(raise_exception=True):
            employee = employee_serializer.save()
            return Response(
                {
                    "message": "Employee created successfully.",
                    "data": employee_serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"message": "Validation failed.", "error": employee_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    except Exception as e:
        return Response(
            {"error": f"Failed to create employee: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def EditEmployee(request):
    company = request.query_params.get("company")
    employee = request.query_params.get("employee")

    if not company or not employee:
        return Response(
            {"error": "Company and employee parameters are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        employee = Employees.objects.select_related("employee_details").get(
            id=employee, company_id=company
        )
    except Employees.DoesNotExist:
        return Response(
            {"error": "Employee not found in the company."},
            status=status.HTTP_404_NOT_FOUND,
        )
    employee_data = EmployeeSerializer(employee).data

    return Response({"employee": employee_data})


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def UpdateEmployee(request):
    data = request.data.copy()
    employee = request.query_params.get("employee")
    company = request.query_params.get("company")
    try:
        employee = Employees.objects.get(id=employee, company_id=company)
    except Employees.DoesNotExist:
        return Response(
            {"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND
        )

    employee_updated_details = EmployeeSerializer(employee, data=data, partial=True)
    if employee_updated_details.is_valid():
        employee_updated_details.save()
        return Response(
            {
                "data": employee_updated_details.data,
                "message": "Employee details updated.",
            },
            status=status.HTTP_200_OK,
        )
    else:
        return Response(
            {"error": employee_updated_details.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def GetEmployeeFilterOptions(request):
    company = request.query_params.get("company")
    filter_option = request.query_params.get("filter_option")

    if not company or not filter_option:
        return Response(
            {"error": "company and filter_option are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    filter_option_map = {
        "employee_internal_id": "employee_internal_id",
        "email": "email",
        "first_name": "first_name",
        "last_name": "last_name",
        "designation": "employee_details__designation__name",
        "department": "employee_details__department__name",
        "date_of_joining": "date_of_joining",
    }

    field = filter_option_map.get(filter_option)

    if not field:
        return Response(
            {"error": "Invalid filter_option."}, status=status.HTTP_400_BAD_REQUEST
        )

    queryset = Employees.objects.filter(company=company).exclude(is_superuser=True)

    filter_values = queryset.values_list(field, flat=True).distinct().order_by(field)

    return Response({"values": list(filter_values)}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def GetEmployees(request):
    company = request.query_params.get("company")
    filter_option = request.query_params.get("filter_option")
    filter_value = request.query_params.get("filter_value")

    if not company:
        return Response(
            {"error": "Company required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        company_data = Companies.objects.get(id=company)
    except Companies.DoesNotExist:
        return Response(
            {"error": "Company not found"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        queryset = (
            Employees.objects.filter(company=company)
            .exclude(is_superuser=True)
            .order_by("-id")
        )

        if filter_option and filter_value:
            filter_map = {
                "employee_internal_id": "employee_internal_id__icontains",
                "email": "email__icontains",
                "first_name": "first_name__icontains",
                "last_name": "last_name__icontains",
                "designation": "employee_details__designation__name__icontains",
                "department": "employee_details__department__name__icontains",
                "date_of_joining": "date_of_joining",
            }
            filter_field = filter_map.get(filter_option)
            if filter_field:
                if filter_option == "date_of_joining":
                    queryset = queryset.filter(**{filter_field: filter_value})
                else:
                    queryset = queryset.filter(**{filter_field: filter_value})

        queryset = (
            queryset.select_related("employee_details")
            .prefetch_related(
                "employee_details__department",
                "employee_details__designation",
                "employee_details__reporting_manager",
            )
            .order_by("-id")
        )

        paginator = CustomPageNumberPagination()
        paginated_qs = paginator.paginate_queryset(queryset, request)
        serializer = EmployeeSerializer(paginated_qs, many=True)

        return paginator.get_paginated_response(serializer.data)

    except Exception as e:
        return Response(
            {"error": f"Failed to fetch employees: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def DeleteEmployees(request):
    employee = request.query_params.get("employee")
    company = request.query_params.get("company")

    is_reporting_manager = EmployeeDetails.objects.filter(
        reporting_manager_id=employee
    ).exists()

    if is_reporting_manager:
        return Response(
            {
                "error": "Employee cannot be deleted because they are assigned as a reporting manager."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        employee = Employees.objects.get(
            id=employee, company_id=company, is_deleted=False
        )
        employee.soft_delete()
        return Response({"message": "Employee deleted."}, status=status.HTTP_200_OK)
    except Employees.DoesNotExist:
        return Response(
            {"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND
        )


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def UpdateLeaveBanks(request):
    data = request.data.copy()
    company = request.query_params.get("company")
    employee = request.query_params.get("employee")
    leaves = data.get("leaves", [])

    if not company or not employee:
        return Response(
            {"error": "Company and employee fields are required."},
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
        employee = Employees.objects.get(id=employee, company=company)
    except Employees.DoesNotExist:
        return Response(
            {"error": "Employee not found in the company."},
            status=status.HTTP_404_NOT_FOUND,
        )

    for leave_entry in leaves:
        leave_type = leave_entry.get("id")
        count = leave_entry.get("count")
        if leave_type is None or count is None:
            continue

        try:
            check_leave_type = LeaveTypes.objects.get(id=leave_type, company=company)
        except LeaveTypes.DoesNotExist:
            return Response(
                {"error": "Leave type not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            leave_bank = EmployeeLeaveBank.objects.get(
                employee=employee, leave_type=leave_type, company=company
            )
            leave_bank.total_leaves_by_type = count
            leave_bank.save()
        except EmployeeLeaveBank.DoesNotExist:
            return Response(
                {"error": "Leave bank entry not found for leave type:{leave_type}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return Response(
                {"error": f"Failed to update leave bank: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
    return Response(
        {"message": "Employee leave bank updated successfully."},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def EditLeaveBanks(request):
    company = request.query_params.get("company")
    employee = request.query_params.get("employee")

    try:
        employee_details = Employees.objects.get(id=employee, company=company)
    except Employees.DoesNotExist:
        return Response(
            {"error": "Employee not found in the company."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        data = EmployeeLeaveBank.objects.filter(
            employee=employee,
            company=company,
        )
    except EmployeeLeaveBank.DoesNotExist:
        return Response(
            {"error": "Leave bank data not found."}, status=status.HTTP_404_NOT_FOUND
        )

    leave_bank_data = LeaveBankSerializer(data, many=True)
    return Response(
        {"data": leave_bank_data.data},
        status=status.HTTP_200_OK,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def CalculateAssignSalaryComponents(request):
    data = request.data.copy()
    company = data.get("company")
    employee = data.get("employee")
    gross_salary = float(data.get("gross_salary", 0))
    now = timezone.now()
    current_month = now.month
    current_year = now.year

    try:
        employee_details = Employees.objects.get(id=employee, company=company)
        company_instance = Companies.objects.get(id=company)
    except Employees.DoesNotExist:
        return Response(
            {"error": "Employee not found in the company."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Companies.DoesNotExist:
        return Response(
            {"error": "Company not found."}, status=status.HTTP_400_BAD_REQUEST
        )

    company_salary_components = SalaryComponents.objects.filter(company=company)
    if not company_salary_components.exists():
        return Response(
            {"error": "Salary components not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    conveyance_allowance = 1600
    medical_allowance = 1250

    basic = gross_salary * 0.40
    da = gross_salary * 0.10
    hra = 0.40 * (basic + da)

    pf = 0.12 * (basic + da)
    esi = 0.0075 * (basic + da)

    special_allowance = gross_salary - (
        basic + da + hra + conveyance_allowance + medical_allowance
    )

    component_amounts = {
        "Basic Pay": basic,
        "Dearness Allowance": da,
        "House Rent Allowance": hra,
        "Conveyance Allowance": conveyance_allowance,
        "Medical Allowance": medical_allowance,
        "Special Allowance": special_allowance,
        "PF": pf,
        "ESI": esi,
    }

    total_earnings = (
        basic + da + hra + conveyance_allowance + medical_allowance + special_allowance
    )
    total_deductions = pf + esi
    net_pay = total_earnings - total_deductions

    with transaction.atomic():
        for component_salary_divisions in company_salary_components:

            amount = component_amounts.get(component_salary_divisions.name)
            if amount is None:
                continue

            duplicate_salary_components = EmployeeSalaryComponents.objects.filter(
                employee=employee_details,
                company=company_instance,
                component=component_salary_divisions,
            )

            if duplicate_salary_components.count() > 1:
                keep_id = duplicate_salary_components.order_by("id").first().id
                duplicate_salary_components.exclude(id=keep_id).delete()

            EmployeeSalaryComponents.objects.filter(
                employee=employee_details,
                company=company_instance,
                component=component_salary_divisions,
            ).update(amount=round(amount, 2))

    EmployeePayroll.objects.update_or_create(
        employee=employee_details,
        company=company_instance,
        month=current_month,
        year=current_year,
        defaults={
            "gross_salary": round(gross_salary, 2),
            "total_earnings": round(total_earnings, 2),
            "total_deductions": round(total_deductions, 2),
            "net_pay": round(net_pay, 2),
        },
    )

    return Response(
        {"message": "Salary components calculated and assigned successfully."},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def GetEmployeeSalaryComponents(request):
    company = request.query_params.get("company")
    employee = request.query_params.get("employee")

    try:
        employee_details = Employees.objects.get(id=employee, company=company)
    except Employees.DoesNotExist:
        return Response(
            {"error": "Employee not found in the company."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        data = (
            EmployeePayroll.objects.filter(
                employee=employee,
                company=company,
            )
            .order_by("-year", "-month")
            .first()
        )
    except EmployeePayroll.DoesNotExist:
        return Response(
            {"error": "Payroll data not found."}, status=status.HTTP_404_NOT_FOUND
        )

    payroll_data = EmployeePayrollSerializer(data)
    return Response(
        {"data": payroll_data.data},
        status=status.HTTP_200_OK,
    )
