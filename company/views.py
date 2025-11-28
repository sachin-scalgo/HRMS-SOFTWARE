from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .serializer import (
    DepartmentSerializer,
    DesignationSerializer,
    EmployementTypeSerializer,
    EmployementStatusSerializer,
    SalaryComponentsSerializer,
    LeaveTypesSerializer,
)
from employee.serializer import EmployeeSerializer
from company.models import (
    Departments,
    Designations,
    EmploymentType,
    EmploymentStatus,
    Countries,
    States,
    SalaryComponents,
    LeaveTypes,
)
from employee.models import Employees

# Create your views here.


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def GetDepartments(request):
    print(request.query_params)
    company = request.query_params.get("company")
    departments = Departments.objects.filter(company=company)
    serializer = DepartmentSerializer(departments, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def GetDesignations(request):
    company = request.query_params.get("company")
    designations = Designations.objects.filter(company_id=company)
    serializer = DesignationSerializer(designations, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def GetReportingHeads(request):
    company = request.query_params.get("company")
    reporting_heads = Employees.objects.filter(company_id=company).exclude(
        id=request.user.id
    )
    reporting_heads = EmployeeSerializer(reporting_heads, many=True)
    return Response(reporting_heads.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def GetEmploymentType(request):
    company = request.query_params.get("company")
    employment_type = EmploymentType.objects.filter(company_id=company)
    employement_type_details = EmployementTypeSerializer(employment_type, many=True)
    return Response(employement_type_details.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def GetEmploymentStatus(request):
    company = request.query_params.get("company")
    employment_status = EmploymentStatus.objects.filter(company_id=company)
    employement_status_details = EmployementStatusSerializer(
        employment_status, many=True
    )
    return Response(employement_status_details.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def GetCountryStates(request):

    company = request.query_params.get("company")

    if not company:
        return Response(
            {"error": "Company required."}, status=status.HTTP_400_BAD_REQUEST
        )
    countries = Countries.objects.filter(company_id=company).order_by("name")
    data = []
    for country in countries:
        states = States.objects.filter(country=country).order_by("name")
        state_list = [{"id": state.id, "name": state.name} for state in states]

        data.append(
            {
                "country_id": country.id,
                "country_name": country.name,
                "states": state_list,
            }
        )

    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def GetSalaryComponents(request):
    company = request.query_params.get("company")
    salary_components = SalaryComponents.objects.filter(company=company)
    salary_component_details = SalaryComponentsSerializer(salary_components, many=True)
    return Response(salary_component_details.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def GetLeaveTypes(request):
    company = request.query_params.get("company")
    leave_types = LeaveTypes.objects.filter(company=company)
    leave_type_details = LeaveTypesSerializer(leave_types, many=True)
    return Response(leave_type_details.data)
