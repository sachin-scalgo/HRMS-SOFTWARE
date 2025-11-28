from django.db import models
from employee.models import Employees

SUBSCRIPTION_CHOICES = [
    ("Free", "Free"),
    ("Basic", "Basic"),
    ("Premium", "Premium"),
]


class Companies(models.Model):
    name = models.CharField(max_length=255)
    registration_number = models.CharField(unique=True, max_length=100)
    tax_id = models.CharField(unique=True, max_length=100, null=True, blank=True)
    address = models.CharField(max_length=255)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(unique=True, max_length=100)
    phone = models.CharField(max_length=20)
    website = models.URLField(max_length=255, null=True, blank=True)
    industry = models.CharField(max_length=100, null=True, blank=True)
    number_of_employees = models.BigIntegerField()
    logo = models.ImageField(upload_to="company_logo/", null=True, blank=True)
    subscription_type = models.CharField(
        max_length=25, choices=SUBSCRIPTION_CHOICES, null=True, blank=True
    )
    notes = models.TextField(null=True, blank=True)
    admin_user = models.OneToOneField(
        "employee.Employees",
        on_delete=models.RESTRICT,
        related_name="company_admin",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "companies"


class Departments(models.Model):
    name = models.CharField(max_length=50)
    company = models.ForeignKey("company.Companies", on_delete=models.RESTRICT)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "departments"


class Designations(models.Model):
    name = models.CharField(max_length=50)
    company = models.ForeignKey("company.Companies", on_delete=models.RESTRICT)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "designations"


class LeaveTypes(models.Model):
    name = models.CharField(max_length=50)
    company = models.ForeignKey("company.Companies", on_delete=models.RESTRICT)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "leave_types"


class Holidays(models.Model):
    name = models.CharField(max_length=50)
    company = models.ForeignKey("company.Companies", on_delete=models.RESTRICT)
    date = models.DateField()
    type = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "holidays"


class SalaryComponents(models.Model):
    company = models.ForeignKey("company.Companies", on_delete=models.RESTRICT)
    name = models.CharField(max_length=50)
    type = models.CharField(max_length=25)
    is_mandatory = models.BooleanField(default=False)
    percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "salary_components"
        unique_together = ("company", "name")


class EmploymentStatus(models.Model):
    company = models.ForeignKey("company.Companies", on_delete=models.RESTRICT)
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "employment_status"
        unique_together = ("company", "name")


class EmploymentType(models.Model):
    company = models.ForeignKey("company.Companies", on_delete=models.RESTRICT)
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "employment_type"
        unique_together = ("company", "name")


class Countries(models.Model):
    company = models.ForeignKey("company.Companies", on_delete=models.RESTRICT)
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "countries"
        unique_together = ("company", "name")


class States(models.Model):
    country = models.ForeignKey("company.Countries", on_delete=models.RESTRICT)
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "states"
        unique_together = ("country", "name")


class MonthlyEffectiveDays(models.Model):
    MONTH_CHOICES = [
        (1, "January"),
        (2, "February"),
        (3, "March"),
        (4, "April"),
        (5, "May"),
        (6, "June"),
        (7, "July"),
        (8, "August"),
        (9, "September"),
        (10, "October"),
        (11, "November"),
        (12, "December"),
    ]

    company = models.ForeignKey(Companies, on_delete=models.RESTRICT)
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField(choices=MONTH_CHOICES)
    effective_days = models.PositiveSmallIntegerField()

    class Meta:
        db_table = "monthly_effective_days"
        unique_together = ("company", "year", "month")
        ordering = ["year", "month"]

    def __str__(self):
        month_name = dict(self.MONTH_CHOICES).get(self.month, self.month)
        return f"{month_name} {self.year} - {self.company.name}"
