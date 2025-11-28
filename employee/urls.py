from django.urls import path
from .views import (
    login_page,
    login,
    logout,
    GetProfile,
    CreateEmployee,
    GetEmployeeFilterOptions,
    RenderEmployee,
    GetEmployees,
    UpdateEmployee,
    EditLeaveBanks,
    DeleteEmployees,
    EditEmployee,
    UpdateLeaveBanks,
    GetEmployeeSalaryComponents,
    CalculateAssignSalaryComponents,
)

urlpatterns = [
    path("login/", login_page, name="login_page"),
    path("employee/login", login, name="login"),
    path("logout", logout, name="logout"),
    path("employee/profile", GetProfile, name="get-employee-profile"),
    path("employee/save", CreateEmployee, name="create-employee"),
    path("employee/update", UpdateEmployee, name="update-employee"),
    path(
        "employee/filter-options",
        GetEmployeeFilterOptions,
        name="employee-filter-options",
    ),
    path("employee/list", RenderEmployee, name="render-employees"),
    path("employee/", GetEmployees, name="list-employees"),
    path("employee/delete", DeleteEmployees, name="delete-employees"),
    path("employee/edit", EditEmployee, name="edit-employees"),
    path("employee/leave-banks/update", UpdateLeaveBanks, name="update-leavebanks"),
    path("employee/leave-banks/edit", EditLeaveBanks, name="edit-leavebanks"),
    path(
        "employee/salary-components/edit",
        GetEmployeeSalaryComponents,
        name="employee-salary-component-edit",
    ),
    path(
        "employee/salary-components/update",
        CalculateAssignSalaryComponents,
        name="employee-salary-component-save",
    ),
]
