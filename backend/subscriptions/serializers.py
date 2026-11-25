from rest_framework import serializers

from .models import BulkHiringRequest, PaymentOrder, SubscriptionPlan, UserSubscription


# ==========================================
# PLANS
# ==========================================

class PublicPlanSerializer(serializers.ModelSerializer):
    """Plan as shown to users on the pricing screen."""

    is_free = serializers.BooleanField(read_only=True)

    class Meta:
        model = SubscriptionPlan
        fields = (
            "id",
            "name",
            "description",
            "price",
            "is_free",
            "validity_days",
            "job_post_limit",
            "max_vacancies_per_job",
            "featured_jobs_included",
            "urgent_jobs_included",
        )
        read_only_fields = fields


class AdminPlanSerializer(serializers.ModelSerializer):
    """Plan create / update by admin."""

    is_free = serializers.BooleanField(read_only=True)

    class Meta:
        model = SubscriptionPlan
        fields = (
            "id",
            "name",
            "description",
            "audience",
            "price",
            "is_free",
            "validity_days",
            "job_post_limit",
            "max_vacancies_per_job",
            "featured_jobs_included",
            "urgent_jobs_included",
            "is_custom",
            "is_active",
            "display_order",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "is_free", "created_by", "created_at", "updated_at")
        extra_kwargs = {
            "price": {"min_value": 0},
            "validity_days": {"min_value": 1, "max_value": 3650},
            "job_post_limit": {"min_value": 1, "max_value": 100000},
            "max_vacancies_per_job": {"min_value": 1, "max_value": 100000},
        }

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Plan name must contain at least 2 characters.")
        return value

    def validate(self, attrs):
        name = attrs.get("name", getattr(self.instance, "name", None))
        is_custom = attrs.get("is_custom", getattr(self.instance, "is_custom", False))

        if name and not is_custom:
            duplicates = SubscriptionPlan.objects.filter(name__iexact=name, is_custom=False)
            if self.instance:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError({"name": "A plan with this name already exists."})

        featured = attrs.get("featured_jobs_included", getattr(self.instance, "featured_jobs_included", 0))
        urgent = attrs.get("urgent_jobs_included", getattr(self.instance, "urgent_jobs_included", 0))
        job_limit = attrs.get("job_post_limit", getattr(self.instance, "job_post_limit", 0))
        if featured > job_limit or urgent > job_limit:
            raise serializers.ValidationError(
                "Featured / urgent jobs included cannot be more than the job post limit."
            )

        return attrs


# ==========================================
# USER SUBSCRIPTIONS
# ==========================================

class UserSubscriptionSerializer(serializers.ModelSerializer):
    """Subscription as shown to its owner."""

    jobs_remaining = serializers.IntegerField(read_only=True)
    is_currently_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserSubscription
        fields = (
            "id",
            "plan",
            "plan_name",
            "price_paid",
            "validity_days",
            "job_post_limit",
            "jobs_used",
            "jobs_remaining",
            "max_vacancies_per_job",
            "featured_jobs_included",
            "featured_used",
            "urgent_jobs_included",
            "urgent_used",
            "status",
            "source",
            "is_currently_active",
            "starts_at",
            "ends_at",
            "created_at",
        )
        read_only_fields = fields


class AdminSubscriptionSerializer(UserSubscriptionSerializer):
    """Subscription as shown to admin (includes who and why)."""

    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_mobile = serializers.CharField(source="user.mobile_number", read_only=True)

    class Meta(UserSubscriptionSerializer.Meta):
        fields = UserSubscriptionSerializer.Meta.fields + (
            "user",
            "user_email",
            "user_mobile",
            "activated_by",
            "admin_note",
            "updated_at",
        )
        read_only_fields = fields
        
# ==========================================
# PAYMENT ORDERS
# ==========================================

class PaymentOrderSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="subscription.plan_name", read_only=True)
    can_retry = serializers.SerializerMethodField()

    class Meta:
        model = PaymentOrder
        fields = (
            "id",
            "razorpay_order_id",
            "razorpay_payment_id",
            "amount_paise",
            "currency",
            "status",
            "status_reason",
            "plan_name",
            "subscription",
            "can_retry",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_can_retry(self, obj):
        if obj.status == PaymentOrder.Status.PAID:
            return False
        from django.utils import timezone
        age = timezone.now() - obj.created_at
        return age.total_seconds() <= 30 * 60
    
    

# ==========================================
# BULK HIRING REQUESTS
# ==========================================

class BulkHiringRequestSerializer(serializers.ModelSerializer):
    """Request as shown to its owner."""

    subscription = UserSubscriptionSerializer(read_only=True)

    class Meta:
        model = BulkHiringRequest
        fields = (
            "id",
            "title",
            "description",
            "number_of_workers",
            "expected_duration_days",
            "location",
            "status",
            "admin_note",
            "subscription",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id", "status", "admin_note", "subscription",
            "created_at", "updated_at",
        )

    def validate_title(self, value):
        value = value.strip()
        if len(value) < 5:
            raise serializers.ValidationError("Title must be at least 5 characters.")
        return value

    def validate_description(self, value):
        value = value.strip()
        if len(value) < 20:
            raise serializers.ValidationError("Please describe your requirement in at least 20 characters.")
        return value

    def validate_number_of_workers(self, value):
        if value < 2:
            raise serializers.ValidationError("Bulk hiring requires at least 2 workers.")
        return value

    def validate_expected_duration_days(self, value):
        if value < 1:
            raise serializers.ValidationError("Duration must be at least 1 day.")
        return value


class AdminBulkHiringRequestSerializer(BulkHiringRequestSerializer):
    """Request as shown to admin (includes user info)."""

    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_mobile = serializers.CharField(source="user.mobile_number", read_only=True)
    reviewed_by_email = serializers.EmailField(source="reviewed_by.email", read_only=True, default=None)

    class Meta(BulkHiringRequestSerializer.Meta):
        fields = BulkHiringRequestSerializer.Meta.fields + (
            "user",
            "user_email",
            "user_mobile",
            "reviewed_by",
            "reviewed_by_email",
            "reviewed_at",
        )
        read_only_fields = fields
        
        
        
