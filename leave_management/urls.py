from django.urls import path
from . import views 

urlpatterns = [
    path("apply/", views.apply_leave,name="apply-leave"),              
    path("update/<int:leave_id>/",views.update_leave_status, name="update_leave_status"),
    path("list/", views.list_leave_applications, name="list_leave_aaplication"),
    path("edit/",views.edit_leave_application, name="edit_leave_application"),
    path("filter-options/",views.list_leave_filter_options,name="list_leave_filter_options"),
]
