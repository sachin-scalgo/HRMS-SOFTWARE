from rest_framework import serializers
from .models import LeaveApplications

class LeaveApplySerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    leave_status_display = serializers.SerializerMethodField()
    employee_internal_id = serializers.SerializerMethodField()
   
    class Meta:
        model = LeaveApplications
        fields = [
            'id', 'from_date', 'to_date', 'leave_duration', 'leave_reason',
            'leave_description', 'leave_days_taken', 'leave_status','leave_status_display','employee_internal_id',
            'created_at', 'updated_at', 'employee', 'employee_name', 'leave_type', 'leave_type_name',
            'submitted_to', 'company'
        ]

    def get_employee_name(self, obj):
        full_name = ''
        if obj.employee:
            names = filter(None, [
                getattr(obj.employee, 'first_name', ''),
                getattr(obj.employee, 'middle_name', ''),
                getattr(obj.employee, 'last_name', '')
            ])
            full_name = ' '.join(names)
        return full_name

    def get_employee_internal_id(self, obj):
        if obj.employee:
            return getattr(obj.employee, 'employee_internal_id', '')
        return ''

    def to_representation(self, instance):
        data = super().to_representation(instance)
        try:
            duration = float(data.get('leave_duration', 0))
        except (TypeError, ValueError):
            duration = 0
        if duration == 1.0:
            data['leave_duration'] = "Full day"
        elif duration == 0.5:
            data['leave_duration'] = "Half day"
        else:
            data['leave_duration'] = str(duration)
        return data
 
    def get_leave_status_display(self, obj):
        status_map = {
            LeaveApplications.PENDING: "Pending",
            LeaveApplications.APPROVED: "Approved",
            LeaveApplications.REJECTED: "Rejected",
            LeaveApplications.REVOKED: "Revoked",
            LeaveApplications.CANCELLED: "Cancelled",
        }
        return status_map.get(obj.leave_status, "Unknown")
