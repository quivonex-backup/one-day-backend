from django.contrib import admin

from .models import (
    State,
    District,
    Taluka,
    Location,
    Skill,
    Language,
    JobCategory,
    JobType,
    EducationLevel,
    ExperienceLevel,
    EmploymentType,
    JobSubCategory,
)


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "state_code", "is_active")
    search_fields = ("name", "state_code")
    list_filter = ("is_active",)


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "state", "district_code", "is_active")
    search_fields = ("name",)
    list_filter = ("state", "is_active")


@admin.register(Taluka)
class TalukaAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "district", "is_active")
    search_fields = ("name",)
    list_filter = ("district", "is_active")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "taluka", "pincode", "is_active")
    search_fields = ("name", "pincode")
    list_filter = ("taluka", "is_active")


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(JobCategory)
class JobCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(JobType)
class JobTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(EducationLevel)
class EducationLevelAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "display_order", "is_active")
    search_fields = ("name",)
    ordering = ("display_order",)


@admin.register(ExperienceLevel)
class ExperienceLevelAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "min_year",
        "max_year",
        "display_order",
        "is_active",
    )
    search_fields = ("name",)
    ordering = ("display_order",)


@admin.register(EmploymentType)
class EmploymentTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)
    
################

# Job Subcategory Admin
@admin.register(JobSubCategory)
class JobSubCategoryAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "category",
        "is_active",
    )

    search_fields = (
        "name",
        "category__name",
    )

    list_filter = (
        "category",
        "is_active",
    )

    autocomplete_fields = (
        "category",
    )

    ordering = ("name",)
