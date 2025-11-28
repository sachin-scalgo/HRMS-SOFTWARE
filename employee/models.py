from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.utils import timezone
from django.db import transaction

# from company.models import EmploymentStatus, EmploymentType

GENDER_CHOICES = [
    ("Male", "Male"),
    ("Female", "Female"),
    ("Other", "Other"),
]

BLOOD_GROUP_CHOICES = [
    ("A+", "A+"),
    ("A-", "A-"),
    ("B+", "B+"),
    ("B-", "B-"),
    ("AB+", "AB+"),
    ("AB-", "AB-"),
    ("O+", "O+"),
    ("O-", "O-"),
]

MARITAL_STATUS_CHOICES = [
    ("Single", "Single"),
    ("Married", "Married"),
    ("Divorced", "Divorced"),
    ("Widowed", "Widowed"),
]

EMPLOYMENT_TYPE_CHOICES = [
    ("Full Time", "Full Time"),
    ("Contract", "Contract"),
]

EMPLOYMENT_STATUS_CHOICES = [
    ("Probation", "Probation"),
    ("Confirmed", "Confirmed"),
    ("Notice Period", "Notice Period"),
    ("Relieved", "Relieved"),
]


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def get_by_natural_key(self, email):
        return self.get(email=email)


class UserSoftDeleteManager(BaseUserManager, SoftDeleteManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class Employees(AbstractUser):
    first_name = models.CharField(max_length=255)
    middle_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255)
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    employee_internal_id = models.CharField(
        max_length=100, unique=True, null=True, blank=True
    )
    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    nationality = models.ForeignKey(
        "company.Countries", on_delete=models.SET_NULL, null=True, blank=True
    )
    state = models.ForeignKey(
        "company.States", on_delete=models.SET_NULL, null=True, blank=True
    )
    city = models.CharField(max_length=100)
    street = models.CharField(max_length=100, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    permanent_address = models.CharField(max_length=255)
    current_address = models.CharField(max_length=255, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10, choices=GENDER_CHOICES, null=True, blank=True
    )
    blood_group = models.CharField(
        max_length=10, choices=BLOOD_GROUP_CHOICES, null=True, blank=True
    )
    marital_status = models.CharField(
        max_length=20, choices=MARITAL_STATUS_CHOICES, null=True, blank=True
    )
    date_of_joining = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(
        upload_to="profile_pics/", null=True, blank=True
    )
    employment_type = models.CharField(
        max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, null=True, blank=True
    )
    employment_status = models.CharField(
        max_length=20, choices=EMPLOYMENT_STATUS_CHOICES, null=True, blank=True
    )
    company = models.ForeignKey(
        "company.Companies", on_delete=models.RESTRICT, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "username", "password"]

    class Meta:
        db_table = "employees"

    objects = UserSoftDeleteManager()
    all_objects = models.Manager()

    @transaction.atomic
    def soft_delete(self):
        now = timezone.now()
        self.is_deleted = True
        self.deleted_at = now
        self.save(update_fields=["is_deleted", "deleted_at"])
        if hasattr(self, "employee_details"):
            try:
                employee_detail = self.employee_details
                employee_detail.is_deleted = True
                employee_detail.deleted_at = now
                employee_detail.save(update_fields=["is_deleted", "deleted_at"])
            except EmployeeDetails.DoesNotExist:
                pass


class EmployeeDetails(models.Model):
    employee = models.OneToOneField(
        Employees, on_delete=models.RESTRICT, related_name="employee_details"
    )
    department = models.ForeignKey(
        "company.Departments", on_delete=models.RESTRICT, null=True, blank=True
    )
    designation = models.ForeignKey(
        "company.Designations", on_delete=models.RESTRICT, null=True, blank=True
    )
    date_of_confirmation = models.DateField(null=True, blank=True)
    reporting_manager = models.ForeignKey(
        Employees,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="team_members",
    )
    work_location = models.CharField(max_length=255, null=True, blank=True)
    bank_account_number = models.CharField(max_length=100, null=True, blank=True)
    bank_account_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    ifsc_code = models.CharField(max_length=50, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "employee_details"

    objects = UserSoftDeleteManager()
    all_objects = models.Manager()


class EmployeeLeaveBank(models.Model):
    employee = models.ForeignKey("employee.Employees", on_delete=models.RESTRICT)
    company = models.ForeignKey(
        "company.Companies", on_delete=models.RESTRICT, null=True, blank=True
    )
    leave_type = models.ForeignKey(
        "company.LeaveTypes", on_delete=models.RESTRICT, null=True, blank=True
    )
    total_leaves_by_type = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, default=0
    )
    remaining_leaves_by_type = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, default=0
    )
    is_cumulated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "employee_leave_banks"
