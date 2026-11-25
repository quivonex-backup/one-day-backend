from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from rest_framework import serializers
from pathlib import Path
from django.core.files import File
from accounts.models import UserProfile
from jobs.models import Job
from .models import JobApplication


class JobApplicationSerializer(serializers.ModelSerializer):

    class Meta:
        model = JobApplication
        fields = "__all__"

        read_only_fields = (
            "applicant",
            "resume",
            "status",
            "employer_remark",
            "applied_at",
            "updated_at",
            "is_active",
        )

    # ==========================
    # Field Validation
    # ==========================

    def validate_cover_letter(self, value):
        if value:
            value = value.strip()

            if len(value) < 20:
                raise serializers.ValidationError(
                    "Cover letter should contain at least 20 characters."
                )

        return value

    def validate_expected_salary(self, value):

        if value < 0:
            raise serializers.ValidationError(
                "Expected salary cannot be negative."
            )

        return value

    # ==========================
    # Object Validation
    # ==========================

    def validate(self, attrs):

        request = self.context.get("request")

        if request is None:
            return attrs

        job = attrs.get(
            "job",
            getattr(self.instance, "job", None)
        )

        if job is None:
            raise serializers.ValidationError({
                "job": "Job is required."
            })

        # A dual-profile account must not apply to its own job.
        if job.posted_by_id == request.user.pk:
            raise serializers.ValidationError({
                "job": "You cannot apply for your own job."
            })

        # Only active jobs
        if not job.is_active:
            raise serializers.ValidationError({
                "job": "This job is no longer available."
            })

        # Only published jobs
        if job.status != Job.Status.PUBLISHED:
            raise serializers.ValidationError({
                "job": "You can only apply to published jobs."
            })

        # Application deadline
        if job.application_deadline < timezone.now().date():
            raise serializers.ValidationError({
                "job": "Application deadline has expired."
            })

        # Prevent duplicate applications
        # Prevent duplicate applications
        if not self.instance:
            if JobApplication.objects.filter(
                applicant=request.user,
                job=job,
                is_active=True,
            ).exists():
                raise serializers.ValidationError({
                    "job": "You have already applied for this job."
                })

            # Resume is required only if the job poster enabled it.
            try:
                profile = request.user.profile
            except UserProfile.DoesNotExist:
                profile = None

            if job.resume_required and (
                profile is None or not profile.resume
            ):
                raise serializers.ValidationError({
                    "resume": (
                        "This job requires a resume. Upload your resume "
                        "in My Profile before applying."
                    )
                })

            # Copy a profile resume when available, even if this job does
            # not make it mandatory.
            if profile and profile.resume:
                attrs["_profile_resume"] = profile.resume
                
                
            return attrs

    # ==========================
    # Create
    # ==========================

    def create(self, validated_data):
        request = self.context["request"]

        # Resume is absent for applicants who have not uploaded one.
        profile_resume = validated_data.pop(
            "_profile_resume",
            None,
        )

        application = JobApplication(
            applicant=request.user,
            **validated_data,
        )

        # Create a separate resume copy only when the applicant has one.
        if profile_resume:
            original_filename = Path(
                profile_resume.name
            ).name

            with profile_resume.open("rb") as resume_file:
                application.resume.save(
                    original_filename,
                    File(resume_file),
                    save=False,
                )

        application.save()
        return application
    # ==========================
    # Update
    # ==========================

    def update(self, instance, validated_data):

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        return instance


# ==========================================
# PRIVACY-SAFE VIEWS OF AN APPLICATION
# ==========================================
# Job owner sees the applicant's work profile (name, skills, experience,
# district). Phone and email are shown to each side ONLY after hiring.
# Never shown: home address, pincode, exact date of birth.

CONTACT_VISIBLE_STATUSES = {
    JobApplication.Status.HIRED,
    JobApplication.Status.COMPLETED,
}


def get_profile(user):
    try:
        return user.profile
    except ObjectDoesNotExist:
        return None


def calculate_age(date_of_birth):
    if not date_of_birth:
        return None
    today = timezone.localdate()
    return today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )


class ApplicantProfileSerializer(serializers.ModelSerializer):
    """Work profile shown to the job owner. No address, pincode or birth date."""

    skills = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    age = serializers.SerializerMethodField()
    district = serializers.CharField(source="city", read_only=True)

    class Meta:
        model = UserProfile
        fields = (
            "full_name",
            "profile_picture",
            "gender",
            "age",
            "district",
            "state",
            "skills",
            "experience_years",
            "expected_wage",
            "expected_wage_type",
            "about",
        )
        read_only_fields = fields

    def get_age(self, profile):
        return calculate_age(profile.date_of_birth)


def contact_details(user):
    return {
        "mobile_number": user.mobile_number,
        "email": user.email,
    }


class OwnerApplicationSerializer(JobApplicationSerializer):
    """Application as seen by the job owner."""

    job_title = serializers.CharField(source="job.job_title", read_only=True)
    applicant_profile = serializers.SerializerMethodField()
    applicant_contact = serializers.SerializerMethodField()

    def get_applicant_profile(self, application):
        profile = get_profile(application.applicant)
        return ApplicantProfileSerializer(profile).data if profile else None

    def get_applicant_contact(self, application):
        # Contact only after the owner hires this person.
        if application.status in CONTACT_VISIBLE_STATUSES:
            return contact_details(application.applicant)
        return None


class ApplicantApplicationSerializer(JobApplicationSerializer):
    """Application as seen by the applicant."""

    job_title = serializers.CharField(source="job.job_title", read_only=True)
    job_status = serializers.CharField(source="job.status", read_only=True)
    job_address = serializers.CharField(source="job.address", read_only=True)
    job_district = serializers.CharField(source="job.district_name", read_only=True)
    job_state = serializers.CharField(source="job.state_name", read_only=True)
    job_start_date = serializers.DateField(source="job.job_start_date", read_only=True)
    poster_name = serializers.SerializerMethodField()
    poster_contact = serializers.SerializerMethodField()

    def get_poster_name(self, application):
        profile = get_profile(application.job.posted_by)
        if not profile:
            return None
        return profile.business_name or profile.full_name or None

    def get_poster_contact(self, application):
        # Job owner's contact only after this applicant is hired.
        if application.status in CONTACT_VISIBLE_STATUSES:
            return contact_details(application.job.posted_by)
        return None
    
    