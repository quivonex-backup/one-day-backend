from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "reviewer", "review_type", "rating", "created_at")
    list_filter = ("review_type", "rating")
    search_fields = ("reviewer__email",)
    raw_id_fields = ("application", "reviewer")
    readonly_fields = ("created_at", "updated_at")