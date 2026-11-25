from django.db import models

from accounts.models import User
from jobs.models import Job
from common.models import JobSubCategory, JobCategory

class JobApplication(models.Model):

    class Status(models.TextChoices):
        APPLIED = "APPLIED", "Applied"
        SHORTLISTED = "SHORTLISTED", "Shortlisted"
        REJECTED = "REJECTED", "Rejected"
        HIRED = "HIRED", "Hired"
        CANCELLED = "CANCELLED", "Cancelled"
        COMPLETED = "COMPLETED", "Completed"

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="applications"
    )
    
    # Every normal user can apply to jobs owned by another user.
    applicant = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="job_applications",
        null=True, blank=True,
    )

    cover_letter = models.TextField(blank=True)

    resume = models.FileField(upload_to="application_resumes/", blank=True, null=True,)
    
    expected_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.APPLIED,
        db_index=True
    )

    employer_remark = models.TextField(blank=True)

    applied_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "job_applications"

        ordering = ["-applied_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["job", "applicant"],
                name="unique_active_job_applicant",
            )
        ]

        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["applied_at"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.applicant_id or 'legacy'} -> {self.job.job_title}"


