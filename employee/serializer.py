from rest_framework import serializers
from employee.models import Employees, EmployeeDetails, EmployeeLeaveBank
from company.models import (
    Departments,
    Designations,
    LeaveTypes,
    SalaryComponents,
    Countries,
    States,
)
from payroll_management.models import EmployeeSalaryComponents
from django.contrib.auth.hashers import make_password
from django.core.validators import RegexValidator
from django.db import transaction


class ReportingManagerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employees
        fields = ["id", "first_name", "last_name"]


class EmployeeDetailsSerializer(serializers.ModelSerializer):
    department = serializers.PrimaryKeyRelatedField(
        queryset=Departments.objects.all(),
        required=False,
        allow_null=True,
    )
    designation = serializers.PrimaryKeyRelatedField(
        queryset=Designations.objects.all(),
        required=False,
        allow_null=True,
    )
    reporting_manager = serializers.PrimaryKeyRelatedField(
        queryset=Employees.objects.all(),
        allow_null=True,
        write_only=True,
    )

    reporting_manager_details = ReportingManagerSerializer(
        source="reporting_manager", read_only=True
    )

    department_name = serializers.CharField(source="department.name", read_only=True)
    designation_name = serializers.CharField(source="designation.name", read_only=True)

    class Meta:
        model = EmployeeDetails
        exclude = ["employee"]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["reporting_manager"] = rep.pop("reporting_manager_details", None)
        return rep

    def validate(self, data):
        if not data.get("reporting_manager"):
            raise serializers.ValidationError(
                {"reporting_manager": "Reporting manager is required."}
            )
        return data


class EmployeeSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    nationality = serializers.PrimaryKeyRelatedField(
        queryset=Countries.objects.all(),
        required=False,
        allow_null=True,
    )
    state = serializers.PrimaryKeyRelatedField(
        queryset=States.objects.all(),
        required=False,
        allow_null=True,
    )

    password = serializers.CharField(write_only=True, required=True, min_length=8)
    nationality_name = serializers.CharField(source="nationality.name", read_only=True)
    state_name = serializers.CharField(source="state.name", read_only=True)

    employee_details = EmployeeDetailsSerializer(required=True)

    class Meta:
        model = Employees
        fields = "__all__"
        extra_kwargs = {"password": {"write_only": True, "required": True}}

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop("password", None)
        if password is None:
            raise serializers.ValidationError({"password": "This field is required."})
        validated_data["password"] = make_password(password)

        employee_details_data = validated_data.pop("employee_details")
        employee = Employees.objects.create(**validated_data)
        EmployeeDetails.objects.create(employee=employee, **employee_details_data)

        leave_types = LeaveTypes.objects.filter(company=employee.company)
        for leave_type in leave_types:
            EmployeeLeaveBank.objects.create(
                employee=employee, company=employee.company, leave_type=leave_type
            )

        salary_components = SalaryComponents.objects.filter(company=employee.company)
        for salary_component in salary_components:
            EmployeeSalaryComponents.objects.create(
                employee=employee, company=employee.company, component=salary_component
            )

        return employee

    def update(self, instance, validated_data):
        employee_details_data = validated_data.pop("employee_details", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if employee_details_data:
            details_instance = getattr(instance, "employee_details", None)
            if details_instance:
                for attr, value in employee_details_data.items():
                    setattr(details_instance, attr, value)
                details_instance.save()
            else:
                EmployeeDetails.objects.create(
                    employee=instance, **employee_details_data
                )

        return instance

    def get_employee_name(self, obj):
        names = filter(
            None,
            [
                getattr(obj, "first_name", ""),
                getattr(obj, "middle_name", ""),
                getattr(obj, "last_name", ""),
            ],
        )
        return " ".join(names)


class LeaveBankSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeLeaveBank
        fields = "__all__"

    def create(self, validated_data):
        return super().create(validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        decimal_fields = ["total_leaves_by_type", "remaining_leaves_by_type"]

        for field in decimal_fields:
            value = data.get(field)
            if value is not None:
                try:
                    data[field] = float(value)
                except (ValueError, TypeError):
                    pass

        return data


class EmployeeSalaryComponentSerializer(serializers.ModelSerializer):
    component_name = serializers.CharField(source="component.name", read_only=True)

    class Meta:
        model = EmployeeSalaryComponents
        fields = "__all__"

    def create(self, validated_data):
        return super().create(validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
