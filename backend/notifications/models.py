from django.conf import settings
from django.db import models


class Notification(models.Model):

    class NotificationType(models.TextChoices):
        JOB_APPLICATION = "JOB_APPLICATION", "New Application"
        APPLICATION_CANCELLED = "APPLICATION_CANCELLED", "Application Cancelled"
        SHORTLISTED = "SHORTLISTED", "Shortlisted"
        REJECTED = "REJECTED", "Applicant Rejected"
        HIRED = "HIRED", "Hired"
        JOB_COMPLETED = "JOB_COMPLETED", "Job Completed"
        JOB_APPROVED = "JOB_APPROVED", "Job Approved"
        JOB_REJECTED = "JOB_REJECTED", "Job Rejected"
        JOB_CANCELLED = "JOB_CANCELLED", "Job Cancelled"
        PAYMENT_SUCCESS = "PAYMENT_SUCCESS", "Payment Success"
        PAYMENT_FAILED = "PAYMENT_FAILED", "Payment Failed"
        SUBSCRIPTION = "SUBSCRIPTION", "Subscription"
        BULK_HIRING_APPROVED = "BULK_HIRING_APPROVED", "Bulk Hiring Approved"
        BULK_HIRING_REJECTED = "BULK_HIRING_REJECTED", "Bulk Hiring Rejected"
        GENERAL = "GENERAL", "General"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.GENERAL,
    )

    title = models.CharField(max_length=200)

    message = models.TextField()

    is_read = models.BooleanField(default=False, db_index=True)

    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    application = models.ForeignKey(
        "applications.JobApplication",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user_id} - {self.title}"
