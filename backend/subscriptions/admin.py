from django.contrib import admin

from .models import BulkHiringRequest, PaymentOrder, SubscriptionPlan, UserSubscription


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "id", "name", "price", "validity_days", "job_post_limit",
        "max_vacancies_per_job", "is_custom", "is_active", "display_order",
    )
    list_filter = ("is_active", "is_custom", "audience")
    search_fields = ("name",)
    readonly_fields = ("created_by", "created_at", "updated_at")


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "plan_name", "status", "source",
        "jobs_used", "job_post_limit", "starts_at", "ends_at",
    )
    list_filter = ("status", "source")
    search_fields = ("user__email", "user__mobile_number", "plan_name")
    raw_id_fields = ("user", "plan", "activated_by")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PaymentOrder)
class PaymentOrderAdmin(admin.ModelAdmin):
    list_display = (
        "id", "razorpay_order_id", "user", "amount_paise",
        "status", "created_at",
    )
    list_filter = ("status",)
    search_fields = ("razorpay_order_id", "razorpay_payment_id", "user__email")
    raw_id_fields = ("user", "subscription")
    readonly_fields = ("created_at", "updated_at")


@admin.register(BulkHiringRequest)
class BulkHiringRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "title", "number_of_workers",
        "status", "reviewed_by", "created_at",
    )
    list_filter = ("status",)
    search_fields = ("user__email", "title")
    raw_id_fields = ("user", "reviewed_by", "subscription")
    readonly_fields = ("created_at", "updated_at")