from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class SubscriptionPlan(models.Model):
    """A plan created by the admin. Users buy it to post jobs."""

    class Audience(models.TextChoices):
        JOB_POSTER = "JOB_POSTER", "Job Poster"
        APPLICANT = "APPLICANT", "Applicant"

    name = models.CharField(max_length=100)

    description = models.TextField(blank=True)

    audience = models.CharField(
        max_length=20,
        choices=Audience.choices,
        default=Audience.JOB_POSTER,
    )

    price = models.DecimalField(max_digits=10, decimal_places=2)

    validity_days = models.PositiveIntegerField()

    job_post_limit = models.PositiveIntegerField()

    max_vacancies_per_job = models.PositiveIntegerField()

    featured_jobs_included = models.PositiveIntegerField(default=0)

    urgent_jobs_included = models.PositiveIntegerField(default=0)

    is_custom = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    display_order = models.PositiveIntegerField(default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_plans",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subscription_plans"
        ordering = ["display_order", "price", "id"]
        constraints = [
            models.CheckConstraint(condition=Q(price__gte=0), name="plan_price_not_negative"),
            models.CheckConstraint(condition=Q(validity_days__gte=1), name="plan_validity_at_least_1_day"),
            models.CheckConstraint(condition=Q(job_post_limit__gte=1), name="plan_job_limit_at_least_1"),
            models.CheckConstraint(condition=Q(max_vacancies_per_job__gte=1), name="plan_vacancies_at_least_1"),
        ]

    @property
    def is_free(self):
        return self.price == 0

    def __str__(self):
        return f"{self.name} (Rs {self.price})"


class UserSubscription(models.Model):
    """
    One plan bought (or given) to one user.

    Plan limits are COPIED here at purchase time, so later admin
    changes to the plan never change what the user already bought.
    """

    class Status(models.TextChoices):
        PENDING_PAYMENT = "PENDING_PAYMENT", "Pending Payment"
        ACTIVE = "ACTIVE", "Active"
        CANCELLED = "CANCELLED", "Cancelled"

    class Source(models.TextChoices):
        RAZORPAY = "RAZORPAY", "Razorpay"
        FREE = "FREE", "Free Plan"
        ADMIN = "ADMIN", "Activated by Admin"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )

    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )

    plan_name = models.CharField(max_length=100)
    price_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    validity_days = models.PositiveIntegerField()
    job_post_limit = models.PositiveIntegerField()
    max_vacancies_per_job = models.PositiveIntegerField()
    featured_jobs_included = models.PositiveIntegerField(default=0)
    urgent_jobs_included = models.PositiveIntegerField(default=0)

    jobs_used = models.PositiveIntegerField(default=0)
    featured_used = models.PositiveIntegerField(default=0)
    urgent_used = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
        db_index=True,
    )

    source = models.CharField(max_length=20, choices=Source.choices)

    starts_at = models.DateTimeField(null=True, blank=True)

    ends_at = models.DateTimeField(null=True, blank=True, db_index=True)

    activated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activated_subscriptions",
    )

    admin_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_subscriptions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(jobs_used__lte=F("job_post_limit")),
                name="subscription_jobs_used_within_limit",
            ),
        ]

    @classmethod
    def from_plan(cls, user, plan, source, **extra):
        """Build a subscription with a copy of the plan's limits (not saved)."""
        return cls(
            user=user,
            plan=plan,
            plan_name=plan.name,
            price_paid=plan.price,
            validity_days=plan.validity_days,
            job_post_limit=plan.job_post_limit,
            max_vacancies_per_job=plan.max_vacancies_per_job,
            featured_jobs_included=plan.featured_jobs_included,
            urgent_jobs_included=plan.urgent_jobs_included,
            source=source,
            **extra,
        )

    def activate(self, activated_by=None):
        """Start the subscription now. Caller saves it."""
        now = timezone.now()
        self.status = self.Status.ACTIVE
        self.starts_at = now
        self.ends_at = now + timedelta(days=self.validity_days)
        if activated_by is not None:
            self.activated_by = activated_by

    @property
    def is_currently_active(self):
        return (
            self.status == self.Status.ACTIVE
            and self.ends_at is not None
            and self.ends_at > timezone.now()
        )

    @property
    def jobs_remaining(self):
        return max(self.job_post_limit - self.jobs_used, 0)

    def __str__(self):
        return f"{self.user_id} - {self.plan_name} ({self.status})"
    
    
    
class PaymentOrder(models.Model):
    """
    One Razorpay order for one subscription purchase.

    Created when the user clicks "Buy". After the frontend collects
    the payment, it sends the Razorpay response here for verification.
    The webhook acts as a backup in case the frontend call fails.
    """

    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_orders",
    )

    subscription = models.ForeignKey(
        UserSubscription,
        on_delete=models.CASCADE,
        related_name="payment_orders",
    )

    razorpay_order_id = models.CharField(max_length=50, unique=True, db_index=True)

    razorpay_payment_id = models.CharField(max_length=50, blank=True)

    razorpay_signature = models.CharField(max_length=128, blank=True)

    amount_paise = models.PositiveIntegerField()

    currency = models.CharField(max_length=3, default="INR")

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.CREATED,
    )

    status_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payment_orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.razorpay_order_id} ({self.status})"
    
    
class BulkHiringRequest(models.Model):
    """
    A user asks for a large number of workers.

    Admin reviews, creates a custom plan, and approves the request.
    Approval automatically creates and activates a subscription.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending Review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bulk_hiring_requests",
    )

    title = models.CharField(max_length=200)

    description = models.TextField(
        help_text="What kind of workers, how many, where, when, etc.",
    )

    number_of_workers = models.PositiveIntegerField()

    expected_duration_days = models.PositiveIntegerField(
        help_text="How many days do you need the workers for?",
    )

    location = models.CharField(max_length=200, blank=True)

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    admin_note = models.TextField(blank=True)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_bulk_requests",
    )

    reviewed_at = models.DateTimeField(null=True, blank=True)

    subscription = models.OneToOneField(
        UserSubscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bulk_hiring_request",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bulk_hiring_requests"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id} - {self.title} ({self.status})"
    
    
    
