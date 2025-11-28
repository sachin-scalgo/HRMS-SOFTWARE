from django.urls import path
from .views import (
    GetDepartments,
    GetDesignations,
    GetReportingHeads,
    GetEmploymentType,
    GetEmploymentStatus,
    GetCountryStates,
    GetSalaryComponents,
    GetLeaveTypes,
)

urlpatterns = [
    path("departments", GetDepartments, name="list-departments"),
    path("designations", GetDesignations, name="list-designations"),
    path("reportingheads", GetReportingHeads, name="list-reporting-heads"),
    path("employmenttype", GetEmploymentType, name="employment-type"),
    path("employmentstatus", GetEmploymentStatus, name="employment-status"),
    path("countrystates", GetCountryStates, name="country-states"),
    path("salarycomponents", GetSalaryComponents, name="salary-components"),
    path("leavetypes", GetLeaveTypes, name="leave-types"),
]
