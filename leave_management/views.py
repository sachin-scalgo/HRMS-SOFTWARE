from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
from calendar import monthrange
from django.db.models import Sum, Q
from django.db import transaction
from decimal import Decimal
from django.core.mail import EmailMessage
from company.models import LeaveTypes, Holidays, Companies
from employee.models import Employees, EmployeeLeaveBank, EmployeeDetails
from .models import LeaveApplications
from .serializers import LeaveApplySerializer
from django.core.exceptions import ObjectDoesNotExist
from collections import defaultdict
from decimal import Decimal
from django.db import transaction
from employee.pagination import CustomPageNumberPagination


def is_weekend_or_holiday(check_date, company):
    return (
        check_date.weekday() >= 5
        or Holidays.objects.filter(company=company, date=check_date).exists()
    )


def generate_working_days(start, end, company):
    current = start
    working_days = []
    while current <= end:
        if not is_weekend_or_holiday(current, company):
            working_days.append(current)
        current += timedelta(days=1)
    return working_days


def group_consecutive_days(days):
    if not days:
        return []
    days = sorted(days)
    chunks = []
    start = days[0]
    end = days[0]
    for day in days[1:]:
        if (day - end).days == 1:
            end = day
        else:
            chunks.append((start, end))
            start = day
            end = day
    chunks.append((start, end))
    return chunks


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def apply_leave(request):
    data = request.data.copy()
    emp_id = data.get("employee_id")
    comp_id = data.get("company")
    leave_type_id = data.get("leave_type")
    leave_duration = data.get("leave_duration")
    leave_reason = data.get("leave_reason", "").strip()

    if not all([emp_id, comp_id, leave_type_id]):
        return Response(
            {"error": "employee_id, company, and leave_type are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        company = Companies.objects.get(id=comp_id)
    except Companies.DoesNotExist:
        return Response(
            {"error": "Company not found."}, status=status.HTTP_404_NOT_FOUND
        )

    try:
        employee = Employees.objects.get(id=emp_id)
    except Employees.DoesNotExist:
        return Response(
            {"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND
        )

    if employee.company_id != company.id:
        return Response(
            {"error": "Employee not associated with the specified company."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        leave_type = LeaveTypes.objects.get(id=leave_type_id, company_id=company.id)
    except LeaveTypes.DoesNotExist:
        return Response(
            {"error": "Leave type not found for the specified company."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        emp_details = EmployeeDetails.objects.get(employee_id=emp_id)
        reporting_head = emp_details.reporting_manager
        if reporting_head is None:
            return Response(
                {"error": "Reporting manager not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    except EmployeeDetails.DoesNotExist:
        return Response(
            {"error": "Employee details not found."}, status=status.HTTP_404_NOT_FOUND
        )

    # check this code
    try:
        employee = Employees.objects.get(id=emp_id, company_id=comp_id)
        leave_type = LeaveTypes.objects.get(id=leave_type_id, company_id=comp_id)
        # reporting_head = Employees.objects.get(id=rep_head_id)
        company = Companies.objects.get(id=comp_id)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    from_date_str = data.get("from_date")
    to_date_str = data.get("to_date")

    if not from_date_str or not to_date_str:
        return Response(
            {"error": "from_date and to_date are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
        to_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()

    except ValueError:
        return Response(
            {"error": "Invalid date format, expected YYYY-MM-DD."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if LeaveApplications.objects.filter(
        employee=employee,
        leave_status__in=[LeaveApplications.PENDING, LeaveApplications.APPROVED],
        from_date__lte=to_date,
        to_date__gte=from_date,
    ).exists():
        return Response(
            {"error": "You have overlapping pending or approved leave."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    leave_bank = EmployeeLeaveBank.objects.filter(
        employee=employee, leave_type=leave_type
    ).first()
    if not leave_bank:
        return Response(
            {"error": "Leave bank not configured for this leave type and employee."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # check this code
    yearly_leave_types = [
        "sick leave",
        "maternity leave",
        "paternity leave",
        "marriage leave",
    ]
    leave_type_lower = leave_type.name.lower()
    is_yearly_cumulative = leave_type_lower in yearly_leave_types

    monthly_casual_limit = Decimal(2)
    total_yearly_allowed = Decimal(leave_bank.total_leaves_by_type)

    working_days = generate_working_days(from_date, to_date, company)
    leave_records_created = {}
    count_allowed_leave_days = Decimal(0)
    count_lop_leave_days = Decimal(0)

    leave_duration_decimal = Decimal(str(leave_duration)) if leave_duration else Decimal('1')

    if from_date == to_date and leave_duration_decimal < 1:
        leave_data = data.copy()
        leave_data.update({
            "employee": employee.id,
            "leave_days_taken": float(leave_duration_decimal),
            "leave_type": leave_type.id,
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "is_lop": False,
            "leave_duration": float(leave_duration_decimal),
            "leave_status": LeaveApplications.PENDING,
            "submitted_to": reporting_head.id,
            "leave_reason": leave_reason,
            "company": company.id,
        })
        serializer = LeaveApplySerializer(data=leave_data)
        if serializer.is_valid():
            obj = serializer.save()
            leave_records_created = {f"allowed_leave_{from_date.isoformat()}": serializer.data}
            count_allowed_leave_days = leave_duration_decimal
            count_lop_leave_days = Decimal('0')
            message = f"Leave applied with {float(count_allowed_leave_days)} allowed leave days"
            return Response({
                "message": message,
                "is_lop": False,
                "data": leave_records_created,
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    working_days = generate_working_days(from_date, to_date, company)
    if is_yearly_cumulative:

        year = from_date.year
        year_start = datetime(year, 1, 1).date()
        year_end = datetime(year, 12, 31).date()
        yearly_taken = LeaveApplications.objects.filter(
            employee=employee,
            leave_type=leave_type,
            leave_status__in=[LeaveApplications.PENDING, LeaveApplications.APPROVED],
            from_date__gte=year_start,
            to_date__lte=year_end,
        ).aggregate(total=Sum("leave_days_taken"))["total"] or Decimal("0")
        remaining_yearly = max(total_yearly_allowed - yearly_taken, Decimal("0"))

        allowed_days = working_days[: int(remaining_yearly)]
        lop_days = working_days[int(remaining_yearly) :]

        def create_leave_entries(days_list, leave_type_id, is_lop_flag):
            chunks = group_consecutive_days(days_list)
            results = {}
            for start_day, end_day in chunks:
                working_days_count = len([d for d in (start_day + timedelta(n) for n in range((end_day - start_day).days + 1)) if not is_weekend_or_holiday(d, company)])
                leave_data.update({
                    "employee": employee.id,
                    "leave_days_taken": float(working_days_count),
                    "leave_type": leave_type_id,
                    "from_date": start_day.isoformat(),
                    "to_date": end_day.isoformat(),
                    "is_lop": is_lop_flag,
                    "leave_duration": float(working_days_count),
                    "leave_status": LeaveApplications.PENDING,
                    "submitted_to": reporting_head.id,
                    "submitted_to": reporting_head.id,
                    "leave_reason": leave_reason,
                    "company": company.id,
                })
                serializer = LeaveApplySerializer(data=leave_data)
                if serializer.is_valid():
                    obj = serializer.save()
                    key = f"{'lop_leave' if is_lop_flag else 'allowed_leave'}_{start_day.isoformat()}"
                    results[key] = serializer.data
                else:
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )
            return results


        if allowed_days:
            resp = create_leave_entries(allowed_days, leave_type.id, False)
            if isinstance(resp, Response):
                return resp
            leave_records_created.update(resp)

        if lop_days:
            resp = create_leave_entries(lop_days, 8, True)  
            if isinstance(resp, Response):
                return resp
            leave_records_created.update(resp)

        count_allowed_leave_days = Decimal(len(allowed_days))
        count_lop_leave_days = Decimal(len(lop_days))

    else:

        days_by_month = defaultdict(list)
        for d in working_days:
            days_by_month[(d.year, d.month)].append(d)

        yearly_taken = LeaveApplications.objects.filter(
            employee=employee,
            leave_type=leave_type,
            leave_status__in=[LeaveApplications.PENDING, LeaveApplications.APPROVED],
        ).aggregate(total=Sum("leave_days_taken"))["total"] or Decimal("0")

        remaining_yearly = max(total_yearly_allowed - yearly_taken, Decimal("0"))

        allowed_days = []
        lop_days = []
        for (year, month), days in sorted(days_by_month.items()):
            month_start = datetime(year, month, 1).date()
            month_end = datetime(year, month, monthrange(year, month)[1]).date()
            monthly_taken = LeaveApplications.objects.filter(
                employee=employee,
                leave_type=leave_type,
                leave_status__in=[
                    LeaveApplications.PENDING,
                    LeaveApplications.APPROVED,
                ],
                from_date__gte=month_start,
                to_date__lte=month_end,
            ).aggregate(total=Sum("leave_days_taken"))["total"] or Decimal("0")

            remaining_monthly = max(monthly_casual_limit - monthly_taken, Decimal("0"))

            for day in sorted(days):
                if remaining_monthly > 0 and remaining_yearly > 0:
                    allowed_days.append(day)
                    remaining_monthly -= Decimal("1")
                    remaining_yearly -= Decimal("1")
                else:
                    lop_days.append(day)

        def create_leave_entries(days_list, leave_type_id, is_lop_flag):
            chunks = group_consecutive_days(days_list)
            results = {}
            for start_day, end_day in chunks:
                working_days_count = len(
                    [
                        d
                        for d in (
                            start_day + timedelta(n)
                            for n in range((end_day - start_day).days + 1)
                        )
                        if not is_weekend_or_holiday(d, company)
                    ]
                )
                leave_data = data.copy()
                leave_data.update({
                    "employee": employee.id,
                    "leave_days_taken": float(working_days_count),
                    "leave_type": leave_type_id,
                    "from_date": start_day.isoformat(),
                    "to_date": end_day.isoformat(),
                    "is_lop": is_lop_flag,
                    "leave_duration": float(working_days_count),
                    "leave_status": LeaveApplications.PENDING,
                    "submitted_to": reporting_head.id,
                    "leave_reason": leave_reason,
                    "company": company.id,
                })
                serializer = LeaveApplySerializer(data=leave_data)
                if serializer.is_valid():
                    obj = serializer.save()
                    key = f"{'lop_leave' if is_lop_flag else 'allowed_leave'}_{start_day.isoformat()}"
                    results[key] = serializer.data
                else:
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )
            return results

        if allowed_days:
            resp = create_leave_entries(allowed_days, leave_type.id, False)
            if isinstance(resp, Response):
                return resp
            leave_records_created.update(resp)

        if lop_days:
            resp = create_leave_entries(lop_days, 8, True)  
            if isinstance(resp, Response):
                return resp
            leave_records_created.update(resp)

        count_allowed_leave_days = Decimal(len(allowed_days))
        count_lop_leave_days = Decimal(len(lop_days))

    message = f"Leave applied with {float(count_allowed_leave_days)} allowed leave days"
    if count_lop_leave_days > 0:
        message += f" and {float(count_lop_leave_days)} Leave Without Pay (LOP) days."

    admin_user = Employees.objects.filter(is_superuser=True).first()
    to_emails = [admin_user.email] if admin_user and admin_user.email else []
    cc_emails = [reporting_head.email] if reporting_head.email else []
    cc_emails.append("ericjkdonna@gmail.com")
    email_subject = "New Leave Application"

    leave_type_name = leave_type.name
    employee_name = employee.get_full_name()
    employee_designation = (
        employee.designation if hasattr(employee, "designation") else "N/A"
    )
    leave_reason_text = leave_reason
    total_leave_days = float(count_allowed_leave_days + count_lop_leave_days)

    email_body = (
        f"Request for  {leave_type_name}\n"
        f"Employee Name: {employee_name}\n"
        f"Employee Designation: {employee_designation}\n"
        f"Leave Period: {from_date_str} to {to_date_str}\n"
        f"Leave Reason: {leave_reason_text}\n"
        f"Total Leave Days Requested: {total_leave_days}\n"
    )

    email = EmailMessage(
        subject=email_subject,
        body=email_body,
        from_email="no-reply@gmail.com",
        to=to_emails,
        cc=cc_emails,
    )
    try:
        email.send(fail_silently=True)
    except Exception:
        pass

    email = EmailMessage(
        subject=email_subject,
        body=email_body,
        from_email="no-reply@gmail.com",
        to=to_emails,
        cc=cc_emails,
    )
    try:
        email.send(fail_silently=True)
    except Exception:
        pass
    return Response(
        {
            "message": message,
            "is_lop": count_lop_leave_days > 0,
            "data": leave_records_created,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def update_leave_status(request, leave_id):
    try:
        leave = LeaveApplications.objects.select_for_update().get(id=leave_id)
    except LeaveApplications.DoesNotExist:
        return Response({"error": "Leave not found"}, status=status.HTTP_404_NOT_FOUND)

    if leave.employee is None:
        return Response({"error": "Associated employee not found"}, status=status.HTTP_404_NOT_FOUND)

    action = request.data.get("action")

    if action == "cancel":
        if leave.leave_status != LeaveApplications.PENDING:
            return Response({"error": "Only pending leaves can be cancelled"}, status=status.HTTP_400_BAD_REQUEST)
        leave.leave_status = LeaveApplications.CANCELLED
        leave.save()

    elif action == "approve":
        if leave.leave_status == LeaveApplications.APPROVED:
            return Response({"error": "Leave already approved"}, status=status.HTTP_400_BAD_REQUEST)
        leave.leave_status = LeaveApplications.APPROVED
        leave.save()

        try:
            leave_bank = EmployeeLeaveBank.objects.select_for_update().get(employee=leave.employee, leave_type=leave.leave_type)
            leave_days = Decimal(str(leave.leave_days_taken))
            remaining = leave_bank.remaining_leaves_by_type or Decimal('0')
            leave_bank.remaining_leaves_by_type = max(remaining - leave_days, Decimal('0'))
            leave_bank.save()
        except EmployeeLeaveBank.DoesNotExist:
            pass

    elif action == "reject":
        leave.leave_status = LeaveApplications.REJECTED
        leave.save()

    elif action == "revoke":
        if leave.leave_status != LeaveApplications.APPROVED:
            return Response({"error": "Only approved leaves can be revoked"}, status=status.HTTP_400_BAD_REQUEST)
        leave.leave_status = LeaveApplications.REVOKED
        leave.save()

        try:
            leave_bank = EmployeeLeaveBank.objects.select_for_update().get(
                employee=leave.employee, leave_type=leave.leave_type
            )
            leave_days = Decimal(str(leave.leave_days_taken))
            remaining = leave_bank.remaining_leaves_by_type or Decimal('0')
            leave_bank.remaining_leaves_by_type = remaining + leave_days
            leave_bank.save()
        except EmployeeLeaveBank.DoesNotExist:
            pass

    else:
        return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        if leave.submitted_to:
            reporting_head_email = leave.submitted_to.email
        else:
            reporting_head_email = None

        admin_user = Employees.objects.filter(is_superuser=True).first()
        admin_email = admin_user.email if admin_user else None

        to_emails = []
        cc_emails = []

    
        if leave.employee and leave.employee.email:
            to_emails.append(leave.employee.email)
    
        if reporting_head_email:
            cc_emails.append(reporting_head_email)

        subject = f"Leave {action.capitalize()} Notification for {leave.employee.get_full_name()}"
        body = (
            f"Leave ID: {leave.id}\n"
            f"Employee: {leave.employee.get_full_name()} ({leave.employee.employee_internal_id})\n"
            f"Leave Type: {leave.leave_type.name}\n"
            f"Leave Period: {leave.from_date.isoformat()} to {leave.to_date.isoformat()}\n"
            f"Leave Days: {leave.leave_days_taken}\n"
            f"Status: {leave.get_leave_status_display()}\n"
            f"Action Taken: {action.capitalize()}\n"
        )

        email = EmailMessage(
            subject=subject,
            body=body,
            from_email="no-reply@gmail.com",
            to=to_emails,
            cc=cc_emails,
        )
        email.send(fail_silently=True)
    except Exception:
        pass


    return Response({"message": f"Leave {action}ed successfully"}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_leave_applications(request):
    user = request.user
    company_id = request.query_params.get("company_id")
    filter_option = request.query_params.get("filter_option")
    filter_value = request.query_params.get("filter_value")

    if not company_id:
        return Response(
            {"error": "company_id is required as a query parameter."},
            status=status.HTTP_400_BAD_REQUEST,
        )

   
    if user.is_superuser:
        leaves = LeaveApplications.objects.filter(company_id=company_id)
    else:
        try:
            employee = Employees.objects.get(email=user.email)
        except Employees.DoesNotExist:
            return Response({"error": "Employee record not found."}, status=404)

        reporting_employee_ids = EmployeeDetails.objects.filter(
            reporting_manager=employee
        ).values_list("employee_id", flat=True)

        leaves = LeaveApplications.objects.filter(
            Q(employee=employee) | Q(employee__in=reporting_employee_ids),
            company_id=company_id,
        )

    if filter_option and filter_value:
        filter_map = {
            "employee_internal_id": "employee__employee_internal_id__icontains",
            "first_name": "employee__first_name__icontains",
            "last_name": "employee__last_name__icontains",
        }
        filter_field = filter_map.get(filter_option)
        if filter_option and filter_value and filter_option in filter_map:
            leaves = leaves.filter(**{filter_field: filter_value})


    
    paginator = CustomPageNumberPagination()
    paginated_qs = paginator.paginate_queryset(leaves, request)
    serializer = LeaveApplySerializer(paginated_qs, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def edit_leave_application(request):
    company = request.query_params.get("company")
    employee = request.query_params.get("employee")
    id = request.query_params.get("id")

    try:
        leave_application = LeaveApplications.objects.get(
            company=company,
            employee=employee,
            id=id
        )
    except LeaveApplications.DoesNotExist:
        return Response(
            {"error": "Leave Application not found."}, status=status.HTTP_404_NOT_FOUND
        )

    serializer = LeaveApplySerializer(leave_application)
    return Response(
        {"data": serializer.data},
        status=status.HTTP_200_OK,
    )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_leave_filter_options(request):
    company = request.query_params.get("company")
    filter_option = request.query_params.get("filter_option")

    if not company or not filter_option:
        return Response({"error": "company and filter_option are required."}, status=status.HTTP_400_BAD_REQUEST)

    filter_option_map = {
        "employee_internal_id": "employee__employee_internal_id",
        "first_name": "employee__first_name",
        "last_name": "employee__last_name",
    }

    field = filter_option_map.get(filter_option)
    if not field:
        return Response({"error": "Invalid filter_option."}, status=status.HTTP_400_BAD_REQUEST)

 
    queryset = LeaveApplications.objects.filter(company=company)

   
    filter_values = queryset.values_list(field, flat=True).distinct().order_by(field)

    return Response({"values": list(filter_values)}, status=status.HTTP_200_OK)
