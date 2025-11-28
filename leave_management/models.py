from django.db import models
from django.utils import timezone
from decimal import Decimal


# Create your models here.
class LeaveApplications(models.Model):

    PENDING = 0
    APPROVED = 1
    REJECTED = 2
    REVOKED = 3
    CANCELLED = 4


    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
        (REVOKED, "Revoked"),
        (CANCELLED, "Cancelled"),
    ]

    employee = models.ForeignKey(
        "employee.Employees",
        on_delete=models.RESTRICT,
        related_name="leave_applications",
    )
    leave_type = models.ForeignKey("company.LeaveTypes", on_delete=models.RESTRICT)
    from_date = models.DateField()
    to_date = models.DateField(null=True, blank=True)
    leave_duration = models.DecimalField(max_digits=3,decimal_places=1)
    leave_reason = models.CharField(max_length=255, null=True, blank=True)
    leave_description = models.CharField(max_length=255, null=True, blank=True)
    leave_days_taken = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    leave_status = models.IntegerField(choices=STATUS_CHOICES, default=PENDING)
    submitted_to = models.ForeignKey(
        "employee.Employees",
        on_delete=models.RESTRICT,
        related_name="leave_approvals",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        "company.Companies", on_delete=models.RESTRICT, null=True, blank=True
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "leave_applications"

    def __str__(self):
        return f"Leave #{self.id} - {self.employee} - {self.get_leave_status_display()}"
