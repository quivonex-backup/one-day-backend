from django.contrib import admin

from .models import User, UserProfile, OTPVerification


@admin.register(User)
class UserAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "email",
        "mobile_number",
        "is_superuser",
        "is_email_verified",
        "is_mobile_verified",
        "is_active",
        "is_staff",
        "created_at",
    )

    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "is_email_verified",
        "is_mobile_verified",
    )

    search_fields = (
        "email",
        "mobile_number",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "last_login",
    )

    ordering = ("-created_at",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "full_name",
        "gender",
        "created_at",
    )

    search_fields = (
        "full_name",
        "user__email",
        "user__mobile_number",
    )

    list_filter = (
        "gender",
    )

    autocomplete_fields = (
        "user",
    )

    ordering = ("-created_at",)


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "otp_type",
        "otp",
        "is_verified",
        "expires_at",
        "created_at",
    )

    search_fields = (
        "user__email",
        "user__mobile_number",
        "otp",
    )

    list_filter = (
        "otp_type",
        "is_verified",
    )

    autocomplete_fields = (
        "user",
    )

    ordering = ("-created_at",)
