from django.shortcuts import render
from employee.views import GetProfile


# Create your views here.
def base_context(request):
    context = {}
    if request.user.is_authenticated:
        user_profile = GetProfile(request.user)
        context["menu"] = get_role_based_menu(user_profile["admin"])
    return context


def get_role_based_menu(is_admin):
    if is_admin:
        return [
            {
                "name": "Admin Dashboard",
                "url": "/dashboard/",
            },
            {"name": "Employees", "url": "employee"},
            {
                "name": "Leave Approvals",
                "url": "/leaves/approvals/",
                "icon": "fas fa-calendar-check",
            },
            {"name": "Reports", "url": "/reports/", "icon": "fas fa-chart-bar"},
        ]

    return [
        {"name": "My Dashboard", "url": "/dashboard/", "icon": "fas fa-home"},
        {"name": "My Leaves", "url": "/my-leaves/", "icon": "fas fa-calendar-alt"},
        {"name": "Profile", "url": "/profile/", "icon": "fas fa-user"},
    ]


def dashboard_page(request):
    context = base_context(request)
    context["page_title"] = "Dashboard"
    return render(request, "dashboard.html", context)
