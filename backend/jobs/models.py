from django.db import models
from accounts.models import User
from common.models import (
    JobCategory,
    JobSubCategory,
    EmploymentType,
    EducationLevel,
    ExperienceLevel,
    Skill,
    Language,
    PostalLocation,
)

class Job(models.Model):

    class SalaryType(models.TextChoices):
        DAILY = "DAILY", "Daily"
        MONTHLY = "MONTHLY", "Monthly"
        YEARLY = "YEARLY", "Yearly"
        NEGOTIABLE = "NEGOTIABLE", "Negotiable"

    class GenderPreference(models.TextChoices):
        ANY = "ANY", "Any"
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PAYMENT_PENDING = "PAYMENT_PENDING", "Payment Pending"
        PENDING_APPROVAL = "PENDING_APPROVAL", "Pending Approval"
        APPROVED = "APPROVED", "Approved"
        PUBLISHED = "PUBLISHED", "Published"
        REJECTED = "REJECTED", "Rejected"
        CLOSED = "CLOSED", "Closed"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        
    class JobDuration(models.TextChoices):
        ONE_DAY = "ONE_DAY", "One Day"
        SHORT_TERM = "SHORT_TERM", "Short Term"
        PART_TIME = "PART_TIME", "Part Time"
        FULL_TIME = "FULL_TIME", "Full Time"
    
    # Every normal user can post a job.
    posted_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="posted_jobs",
        null=True, blank=True,
    )

    # ==========================
    # Basic Information
    # ==========================

    job_title = models.CharField(max_length=200)

    job_category = models.ForeignKey(JobCategory, on_delete=models.PROTECT, related_name="jobs")

    # Kept optional for older records. The category and subcategory are the
    # classification used by the new unified posting flow.
    employment_type = models.ForeignKey(
        EmploymentType, on_delete=models.PROTECT, related_name="jobs",
        null=True, blank=True,
    )

    job_subcategory = models.ForeignKey(
        JobSubCategory, on_delete=models.PROTECT, related_name="jobs",
        null=True, blank=True,
    )
    
    job_duration = models.CharField(max_length=20, choices=JobDuration.choices)
    
    education_level = models.ForeignKey(EducationLevel, on_delete=models.SET_NULL, null=True, blank=True, related_name="jobs")

    experience_level = models.ForeignKey(ExperienceLevel, on_delete=models.SET_NULL, null=True, blank=True, related_name="jobs")

    resume_required = models.BooleanField(default=False, help_text="Whether applicants must have a resume to apply.",)
    # ==========================
    # Job Description
    # ==========================

    job_description = models.TextField()

    responsibilities = models.TextField(blank=True)

    requirements = models.TextField(blank=True)

    # ==========================
    # Salary
    # ==========================

    salary_type = models.CharField(max_length=20, choices=SalaryType.choices)

    minimum_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    maximum_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    daily_wage = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # ==========================
    # Vacancy
    # ==========================

    number_of_vacancies = models.PositiveIntegerField(default=1)

    # ==========================
    # Skills & Languages
    # ==========================

    skills = models.ManyToManyField(Skill, blank=True, related_name="jobs")

    languages = models.ManyToManyField(Language, blank=True, related_name="jobs")

    # ==========================
    # Location
    # ==========================

    address = models.TextField()
    
    postal_location = models.ForeignKey( PostalLocation, on_delete=models.PROTECT, related_name="jobs", null=True, blank=True,)

    # Auto-filled from postal_location in save(). Frontend must not send these.
    pincode = models.CharField(max_length=6)
    district_name = models.CharField(max_length=150, blank=True, default="")
    state_name = models.CharField(max_length=150, blank=True, default="")

# GPS Coordinates
    job_latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )
    
    job_longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )

    # ==========================
    # Working Details
    # ==========================

    working_days = models.CharField(max_length=100, blank=True)

    start_time = models.TimeField()

    end_time = models.TimeField()

    job_start_date = models.DateField()

    job_end_date = models.DateField()

    application_deadline = models.DateField()

    # ==========================
    # Benefits
    # ==========================

    food_provided = models.BooleanField(default=False)

    accommodation_provided = models.BooleanField(default=False)

    transport_provided = models.BooleanField(default=False)

    # ==========================
    # Candidate Preference
    # ==========================

    gender_preference = models.CharField(max_length=10, choices=GenderPreference.choices, default=GenderPreference.ANY)

    minimum_age = models.PositiveIntegerField(default=18)

    maximum_age = models.PositiveIntegerField(default=60)

    # ==========================
    # Job Status
    # ==========================

    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT, db_index=True)

    approved_by = models.ForeignKey(
    User,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="approved_jobs"
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True
    )
    
    rejected_by = models.ForeignKey(
    User,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="rejected_jobs"
    )

    rejected_at = models.DateTimeField(null=True, blank=True)
    
    
    # Shown to the job owner so they know what to fix.
    rejection_reason = models.TextField(blank=True)

    company_name = models.CharField(max_length=200, blank=True, default="")
    
    is_featured = models.BooleanField(default=False)

    is_urgent = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    # ==========================
    # Audit
    # ==========================

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:

        db_table = "jobs"

        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["job_title"]),
            models.Index(fields=["status"]),
            models.Index(fields=["job_category"]),
            models.Index(fields=["job_subcategory"]),
            models.Index(fields=["employment_type"]),
            models.Index(fields=["pincode"]),
            models.Index(fields=["district_name"]),
            models.Index(fields=["state_name"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["is_active"]),
        ]

    def save(self, *args, **kwargs):
        # Location text always comes from the selected postal record.
        if self.postal_location_id:
            location = self.postal_location
            self.pincode = location.pincode
            self.district_name = location.district_name
            self.state_name = location.state_name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.job_title} - {self.posted_by_id or 'legacy'}"