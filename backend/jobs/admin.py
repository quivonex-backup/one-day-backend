from django.contrib import admin

from .models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "job_title",
        "posted_by",
        "job_category",
        "pincode",
        "district_name",
        "state_name",
        "status",
        "is_featured",
        "is_urgent",
        "is_active",
        "created_at",
    )

    search_fields = (
        "job_title",
        "posted_by__email",
        "pincode",
        "district_name",
    )

    list_filter = (
        "status",
        "job_category",
        "employment_type",
        "state_name",
        "is_featured",
        "is_urgent",
        "is_active",
    )

    filter_horizontal = (
        "skills",
        "languages",
    )

    autocomplete_fields = (
        "posted_by",
        "job_category",
        "job_subcategory",
        "employment_type",
        "education_level",
        "experience_level",
    )

    # 165k postal records: use an ID box instead of a huge dropdown.
    raw_id_fields = ("postal_location",)

    readonly_fields = (
        "pincode",
        "district_name",
        "state_name",
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )