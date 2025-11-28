from rest_framework import serializers
from company.models import (
    Departments,
    Designations,
    EmploymentType,
    EmploymentStatus,
    SalaryComponents,
    LeaveTypes,
    Companies,
)


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Companies
        fields = [
            "id",
            "name",
            "registration_number",
            "tax_id",
            "address",
            "country",
            "state",
            "city",
            "postal_code",
            "email",
            "phone",
            "website",
            "industry",
            "logo",
            "subscription_type",
        ]


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departments
        fields = ["id", "name", "company_id"]


class DesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Designations
        fields = [
            "id",
            "name",
        ]


class EmployementTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmploymentType
        fields = [
            "id",
            "name",
        ]


class EmployementStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmploymentStatus
        fields = [
            "id",
            "name",
        ]


class SalaryComponentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryComponents
        fields = ["id", "name", "is_mandatory"]


class LeaveTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTypes
        fields = ["id", "name"]
