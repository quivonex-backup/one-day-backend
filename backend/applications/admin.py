from django.contrib import admin

from .models import JobApplication


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "job",
        "applicant",
        "status",
        "expected_salary",
        "applied_at",
        "is_active",
    )

    list_filter = (
        "status",
        "is_active",
        "applied_at",
    )

    search_fields = (
        "job__job_title",
        "applicant__profile__full_name",
        "applicant__email",
    )

    readonly_fields = (
        "applied_at",
        "updated_at",
    )

    autocomplete_fields = (
        "job",
        "applicant",
    )

    ordering = (
        "-applied_at",
    )

    list_per_page = 20
