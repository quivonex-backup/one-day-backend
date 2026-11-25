from rest_framework import serializers

from common.models import PostalLocation
from common.serializers import PincodePostalLocationSerializer
from .models import Job


class JobSerializer(serializers.ModelSerializer):

    postal_location_id = serializers.PrimaryKeyRelatedField(
        source="postal_location",
        queryset=PostalLocation.objects.filter(is_active=True),
        write_only=True,
        required=False,)

    # Output: full selected post-office/village details.
    postal_location = PincodePostalLocationSerializer(read_only=True)
    applied_count = serializers.IntegerField(read_only=True, default=None)
    posted_by_label = serializers.SerializerMethodField()
    class Meta:
        model = Job
        fields = "__all__"
        read_only_fields = (
            "posted_by",
            "status",
            "approved_by",
            "approved_at",
            "rejected_by",
            "rejected_at",
            "rejection_reason",
            "is_featured",
            "is_urgent",
            "is_active",
            "created_at",
            "updated_at",
            # Auto-filled from postal_location in Job.save()
            "pincode",
            "district_name",
            "state_name",
        )

    def get_posted_by_label(self, obj):
        if obj.company_name:
            return obj.company_name
        user = obj.posted_by
        if user and hasattr(user, "profile"):
            return user.profile.full_name or user.mobile_number
        if user:
            return user.mobile_number
        return "Unknown"
    
    
    # ==========================
    # Field Validations
    # ==========================

    def validate_job_title(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Job title is required.")

        if len(value) < 3:
            raise serializers.ValidationError(
                "Job title must contain at least 3 characters."
            )

        return value

    def validate_job_description(self, value):
        value = value.strip()

        if len(value) < 20:
            raise serializers.ValidationError(
                "Job description should contain at least 20 characters."
            )

        return value
    
    def validate_address(self, value):
        value = value.strip()
        if len(value) < 5:
            raise serializers.ValidationError(
                "Job address should contain at least 5 characters."
            )
        return value

    # ==========================
    # Object Validation
    # ==========================

    def validate(self, attrs):

        category = attrs.get("job_category", getattr(self.instance, "job_category", None))
        subcategory = attrs.get("job_subcategory", getattr(self.instance, "job_subcategory", None))

        if self.instance is None and not subcategory:
            raise serializers.ValidationError({"job_subcategory": "Job subcategory is required."})

        if subcategory and category and subcategory.category_id != category.id:
            raise serializers.ValidationError({
                "job_subcategory": "The selected subcategory does not belong to this job category."
            })

        postal_location = attrs.get(
            "postal_location",
            getattr(self.instance, "postal_location", None)
        )

        if postal_location is None:
            raise serializers.ValidationError({
                "postal_location_id": "Please select the job post office/village from the pincode lookup."
            })
            
        salary_type = attrs.get(
            "salary_type",
            getattr(self.instance, "salary_type", None)
        )

        minimum_salary = attrs.get(
            "minimum_salary",
            getattr(self.instance, "minimum_salary", 0)
        )

        maximum_salary = attrs.get(
            "maximum_salary",
            getattr(self.instance, "maximum_salary", 0)
        )

        daily_wage = attrs.get(
            "daily_wage",
            getattr(self.instance, "daily_wage", 0)
        )

        vacancies = attrs.get(
            "number_of_vacancies",
            getattr(self.instance, "number_of_vacancies", 1)
        )

        minimum_age = attrs.get(
            "minimum_age",
            getattr(self.instance, "minimum_age", 18)
        )

        maximum_age = attrs.get(
            "maximum_age",
            getattr(self.instance, "maximum_age", 60)
        )

        start_time = attrs.get(
            "start_time",
            getattr(self.instance, "start_time", None)
        )

        end_time = attrs.get(
            "end_time",
            getattr(self.instance, "end_time", None)
        )

        job_start_date = attrs.get(
            "job_start_date",
            getattr(self.instance, "job_start_date", None)
        )

        job_end_date = attrs.get(
            "job_end_date",
            getattr(self.instance, "job_end_date", None)
        )

        application_deadline = attrs.get(
            "application_deadline",
            getattr(self.instance, "application_deadline", None)
        )

        latitude = attrs.get(
            "job_latitude",
            getattr(self.instance, "job_latitude", None)
        )

        longitude = attrs.get(
            "job_longitude",
            getattr(self.instance, "job_longitude", None)
        )

        job_duration = attrs.get(
            "job_duration",
            getattr(self.instance, "job_duration", None)
        )

        # ==========================
        # Job Duration
        # ==========================

        if not job_duration:
            raise serializers.ValidationError({
                "job_duration": "Job duration is required."
            })

        # ==========================
        # Vacancy Validation
        # ==========================

        if vacancies <= 0:
            raise serializers.ValidationError({
                "number_of_vacancies":
                "Number of vacancies must be greater than zero."
            })

        # ==========================
        # Salary Validation
        # ==========================

        if salary_type == Job.SalaryType.DAILY:

            if daily_wage <= 0:
                raise serializers.ValidationError({
                    "daily_wage":
                    "Daily wage must be greater than zero."
                })

        else:

            if minimum_salary <= 0:
                raise serializers.ValidationError({
                    "minimum_salary":
                    "Minimum salary must be greater than zero."
                })

            if maximum_salary <= 0:
                raise serializers.ValidationError({
                    "maximum_salary":
                    "Maximum salary must be greater than zero."
                })

            if minimum_salary > maximum_salary:
                raise serializers.ValidationError({
                    "maximum_salary":
                    "Maximum salary must be greater than minimum salary."
                })

                # ==========================
        # GPS Validation
        # ==========================

        # Latitude and longitude must be provided together
        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError({
                "gps": "Both latitude and longitude are required together."
            })

        if latitude is not None:
            if not -90 <= latitude <= 90:
                raise serializers.ValidationError({
                    "job_latitude": "Invalid latitude."
                })

        if longitude is not None:
            if not -180 <= longitude <= 180:
                raise serializers.ValidationError({
                    "job_longitude": "Invalid longitude."
                })

        # ==========================
        # Age Validation
        # ==========================

        if minimum_age < 18:
            raise serializers.ValidationError({
                "minimum_age":
                "Minimum age cannot be less than 18."
            })

        if minimum_age > maximum_age:
            raise serializers.ValidationError({
                "maximum_age":
                "Maximum age must be greater than minimum age."
            })

        # ==========================
        # Working Time Validation
        # ==========================

        if start_time and end_time:

            if start_time >= end_time:
                raise serializers.ValidationError({
                    "end_time":
                    "End time must be greater than start time."
                })

        # ==========================
        # Date Validation
        # ==========================

        if job_start_date and job_end_date:

            if job_end_date < job_start_date:
                raise serializers.ValidationError({
                    "job_end_date":
                    "Job end date cannot be before start date."
                })

        if application_deadline and job_start_date:

            if application_deadline > job_start_date:
                raise serializers.ValidationError({
                    "application_deadline":
                    "Application deadline must be on or before the job start date."
                })

        return attrs

    # ==========================
    # Create
    # ==========================

    def create(self, validated_data):
        skills = validated_data.pop("skills", [])
        languages = validated_data.pop("languages", [])

        job = Job.objects.create(**validated_data)

        job.skills.set(skills)
        job.languages.set(languages)

        return job

    # ==========================
    # Update
    # ==========================

    def update(self, instance, validated_data):

        skills = validated_data.pop("skills", None)
        languages = validated_data.pop("languages", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if skills is not None:
            instance.skills.set(skills)

        if languages is not None:
            instance.languages.set(languages)

        return instance
