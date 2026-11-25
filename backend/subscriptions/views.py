import hashlib
import hmac
import json
import logging

import razorpay
from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.access import IsAdmin
from .models import BulkHiringRequest, PaymentOrder, SubscriptionPlan, UserSubscription
from .serializers import (
    AdminPlanSerializer,
    AdminSubscriptionSerializer,
    PublicPlanSerializer,
    UserSubscriptionSerializer,
)
from notifications.models import Notification
from notifications.services import notify
from .services import active_subscriptions, has_used_free_plan, posting_summary

logger = logging.getLogger(__name__)


def _get_razorpay_client():
    return razorpay.Client(auth=(django_settings.RAZORPAY_KEY_ID, django_settings.RAZORPAY_KEY_SECRET))


User = get_user_model()


def ok(message, data=None, status_code=status.HTTP_200_OK, **extra):
    body = {"success": True, "message": message}
    if data is not None:
        body["data"] = data
    body.update(extra)
    return Response(body, status=status_code)


def fail(message, status_code=status.HTTP_400_BAD_REQUEST, **extra):
    body = {"success": False, "message": message}
    body.update(extra)
    return Response(body, status=status_code)


def public_plans():
    """Plans users can see and buy."""
    return SubscriptionPlan.objects.filter(
        is_active=True,
        is_custom=False,
        audience=SubscriptionPlan.Audience.JOB_POSTER,
    )


# ==========================================
# PUBLIC / USER APIs
# ==========================================

class PlanListAPIView(APIView):
    """Pricing screen. No login needed."""

    permission_classes = [AllowAny]

    def post(self, request):
        plans = public_plans()
        return ok("Plans fetched successfully.", PublicPlanSerializer(plans, many=True).data, count=plans.count())


class PlanDetailAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        plan = public_plans().filter(id=request.data.get("plan_id")).first()
        if not plan:
            return fail("Plan not found.", status.HTTP_404_NOT_FOUND)
        return ok("Plan fetched successfully.", PublicPlanSerializer(plan).data)


class MySubscriptionsAPIView(APIView):
    """Current user's subscriptions and how many jobs they can still post."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if str(request.data.get("active_only", "")).lower() == "true":
            subscriptions = active_subscriptions(request.user)
        else:
            subscriptions = UserSubscription.objects.filter(user=request.user)
        return ok(
            "Subscriptions fetched successfully.",
            UserSubscriptionSerializer(subscriptions, many=True).data,
            summary=posting_summary(request.user),
        )


class ActivateFreePlanAPIView(APIView):
    """Free plans (price 0) start instantly. Each user can take a free plan only once."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan = public_plans().filter(id=request.data.get("plan_id")).first()
        if not plan:
            return fail("Plan not found.", status.HTTP_404_NOT_FOUND)
        if not plan.is_free:
            return fail("This plan is not free. Please complete the payment to activate it.")

        with transaction.atomic():
            User.objects.select_for_update().get(pk=request.user.pk)

            if has_used_free_plan(request.user):
                return fail("You have already used a free plan.")

            subscription = UserSubscription.from_plan(
                request.user, plan, UserSubscription.Source.FREE,
            )
            subscription.activate()
            subscription.save()

        notify(
            request.user,
            Notification.NotificationType.SUBSCRIPTION,
            "Free Plan Activated",
            f"Your free plan '{plan.name}' is now active. You can post up to {subscription.job_post_limit} jobs.",
        )
        return ok(
            "Free plan activated successfully.",
            UserSubscriptionSerializer(subscription).data,
            status.HTTP_201_CREATED,
        )


# ==========================================
# ADMIN APIs
# ==========================================

class AdminPlanListAPIView(APIView):
    """All plans, including inactive and custom ones."""

    permission_classes = [IsAdmin]

    def post(self, request):
        plans = SubscriptionPlan.objects.all()
        if request.data.get("is_active") is not None:
            plans = plans.filter(is_active=str(request.data["is_active"]).lower() == "true")
        return ok("Plans fetched successfully.", AdminPlanSerializer(plans, many=True).data, count=plans.count())


class AdminCreatePlanAPIView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = AdminPlanSerializer(data=request.data)
        if not serializer.is_valid():
            return fail("Validation error.", errors=serializer.errors)
        plan = serializer.save(created_by=request.user)
        return ok("Plan created successfully.", AdminPlanSerializer(plan).data, status.HTTP_201_CREATED)


class AdminUpdatePlanAPIView(APIView):
    """Changes apply to new purchases only. Existing subscriptions keep their copy."""

    permission_classes = [IsAdmin]

    def post(self, request):
        plan = SubscriptionPlan.objects.filter(id=request.data.get("plan_id")).first()
        if not plan:
            return fail("Plan not found.", status.HTTP_404_NOT_FOUND)
        serializer = AdminPlanSerializer(plan, data=request.data, partial=True)
        if not serializer.is_valid():
            return fail("Validation error.", errors=serializer.errors)
        plan = serializer.save()
        return ok("Plan updated successfully.", AdminPlanSerializer(plan).data)


class AdminSetPlanActiveAPIView(APIView):
    """Hide / show a plan. Plans are never deleted because users bought them."""

    permission_classes = [IsAdmin]

    def post(self, request):
        plan = SubscriptionPlan.objects.filter(id=request.data.get("plan_id")).first()
        if not plan:
            return fail("Plan not found.", status.HTTP_404_NOT_FOUND)
        plan.is_active = str(request.data.get("is_active", "")).lower() == "true"
        plan.save(update_fields=["is_active", "updated_at"])
        return ok("Plan status updated successfully.", AdminPlanSerializer(plan).data)


class AdminActivateSubscriptionAPIView(APIView):
    """
    Give a plan to a user by hand: offline payment (cash / UPI) or a gift.
    Works for any plan, including custom plans made for bulk hiring.
    """

    permission_classes = [IsAdmin]

    def post(self, request):
        user = User.objects.filter(id=request.data.get("user_id"), is_active=True).first()
        if not user:
            return fail("User not found.", status.HTTP_404_NOT_FOUND)

        plan = SubscriptionPlan.objects.filter(id=request.data.get("plan_id"), is_active=True).first()
        if not plan:
            return fail("Plan not found or inactive.", status.HTTP_404_NOT_FOUND)

        note = str(request.data.get("note") or "").strip()
        if len(note) < 5:
            return fail("Please add a note (at least 5 characters), e.g. 'Paid Rs 500 cash on 01-11-2026'.")

        subscription = UserSubscription.from_plan(
            user, plan, UserSubscription.Source.ADMIN, admin_note=note[:1000],
        )
        subscription.activate(activated_by=request.user)
        subscription.save()

        notify(
            user,
            Notification.NotificationType.SUBSCRIPTION,
            "Subscription Activated",
            f"Admin has activated the '{plan.name}' plan for you. You can post up to {subscription.job_post_limit} jobs.",
        )
        return ok(
            "Subscription activated successfully.",
            AdminSubscriptionSerializer(subscription).data,
            status.HTTP_201_CREATED,
        )


class AdminCancelSubscriptionAPIView(APIView):
    """Stop a subscription. Jobs already posted are not touched."""

    permission_classes = [IsAdmin]

    def post(self, request):
        subscription = UserSubscription.objects.filter(id=request.data.get("subscription_id")).first()
        if not subscription:
            return fail("Subscription not found.", status.HTTP_404_NOT_FOUND)
        if subscription.status == UserSubscription.Status.CANCELLED:
            return fail("Subscription is already cancelled.")

        note = str(request.data.get("note") or "").strip()
        if len(note) < 5:
            return fail("Please add a reason (at least 5 characters).")

        subscription.status = UserSubscription.Status.CANCELLED
        subscription.admin_note = (subscription.admin_note + "\nCancelled: " + note).strip()[:2000]
        subscription.save(update_fields=["status", "admin_note", "updated_at"])
        return ok("Subscription cancelled successfully.", AdminSubscriptionSerializer(subscription).data)


class AdminSubscriptionListAPIView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        subscriptions = UserSubscription.objects.select_related("user")
        if request.data.get("user_id"):
            subscriptions = subscriptions.filter(user_id=request.data["user_id"])
        if request.data.get("status"):
            subscriptions = subscriptions.filter(status=request.data["status"])
        return ok(
            "Subscriptions fetched successfully.",
            AdminSubscriptionSerializer(subscriptions, many=True).data,
            count=subscriptions.count(),
        )
        
        
        
        
# ==========================================
# RAZORPAY PAYMENT APIs
# ==========================================

class CreatePaymentOrderAPIView(APIView):
    """
    Step 1 of online payment.

    The user picks a plan. We create:
      - a PENDING_PAYMENT UserSubscription
      - a Razorpay order (amount in paise)
      - a PaymentOrder row linking the two

    The response gives the frontend everything it needs to open the
    Razorpay checkout popup.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan = public_plans().filter(id=request.data.get("plan_id")).first()
        if not plan:
            return fail("Plan not found.", status.HTTP_404_NOT_FOUND)
        if plan.is_free:
            return fail("This is a free plan. Use the free activation endpoint.")

        amount_paise = int(plan.price * 100)

        client = _get_razorpay_client()
        try:
            rz_order = client.order.create({
                "amount": amount_paise,
                "currency": "INR",
                "notes": {
                    "plan_id": str(plan.id),
                    "plan_name": plan.name,
                    "user_id": str(request.user.id),
                    "user_email": request.user.email,
                },
            })
        except Exception as exc:
            logger.error("Razorpay order creation failed: %s", exc)
            return fail(
                "Could not create payment order. Please try again.",
                status.HTTP_502_BAD_GATEWAY,
            )

        subscription = UserSubscription.from_plan(
            request.user, plan, UserSubscription.Source.RAZORPAY,
        )
        subscription.save()

        PaymentOrder.objects.create(
            user=request.user,
            subscription=subscription,
            razorpay_order_id=rz_order["id"],
            amount_paise=amount_paise,
        )

        return ok(
            "Payment order created. Complete the payment in the Razorpay popup.",
            {
                "razorpay_order_id": rz_order["id"],
                "razorpay_key_id": django_settings.RAZORPAY_KEY_ID,
                "amount_paise": amount_paise,
                "currency": "INR",
                "plan_name": plan.name,
                "subscription_id": subscription.id,
            },
            status.HTTP_201_CREATED,
        )


class VerifyPaymentAPIView(APIView):
    """
    Step 2 of online payment.

    The frontend sends us the three values Razorpay returns after a
    successful payment. We verify the signature, mark the order PAID,
    and activate the subscription.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        razorpay_order_id = str(request.data.get("razorpay_order_id") or "").strip()
        razorpay_payment_id = str(request.data.get("razorpay_payment_id") or "").strip()
        razorpay_signature = str(request.data.get("razorpay_signature") or "").strip()

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return fail("razorpay_order_id, razorpay_payment_id and razorpay_signature are required.")

        order = PaymentOrder.objects.select_related("subscription").filter(
            razorpay_order_id=razorpay_order_id,
            user=request.user,
        ).first()
        if not order:
            return fail("Payment order not found.", status.HTTP_404_NOT_FOUND)
        if order.status == PaymentOrder.Status.PAID:
            return ok(
                "Payment already verified.",
                UserSubscriptionSerializer(order.subscription).data,
            )

        expected_signature = hmac.new(
            django_settings.RAZORPAY_KEY_SECRET.encode(),
            f"{razorpay_order_id}|{razorpay_payment_id}".encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, razorpay_signature):
            order.status = PaymentOrder.Status.FAILED
            order.status_reason = "Signature mismatch"
            order.save(update_fields=["status", "status_reason", "updated_at"])
            return fail("Payment verification failed. Signature mismatch.")

        with transaction.atomic():
            order.razorpay_payment_id = razorpay_payment_id
            order.razorpay_signature = razorpay_signature
            order.status = PaymentOrder.Status.PAID
            order.save(update_fields=[
                "razorpay_payment_id", "razorpay_signature", "status", "updated_at",
            ])

            sub = order.subscription
            if sub.status != UserSubscription.Status.ACTIVE:
                sub.activate()
                sub.save()

        notify(
            request.user,
            Notification.NotificationType.PAYMENT_SUCCESS,
            "Payment Successful",
            f"Your payment for '{sub.plan_name}' has been verified. Subscription is now active.",
        )
        return ok(
            "Payment verified. Subscription activated.",
            UserSubscriptionSerializer(sub).data,
        )


class RazorpayWebhookAPIView(APIView):
    """
    Backup: Razorpay POSTs payment events here.

    Handles `payment.captured` (activate) and `payment.failed` (mark failed).
    The webhook secret is verified via HMAC-SHA256 on the raw body.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        signature = request.META.get("HTTP_X_RAZORPAY_SIGNATURE", "")
        webhook_secret = django_settings.RAZORPAY_WEBHOOK_SECRET or ""

        if not webhook_secret:
            logger.warning("RAZORPAY_WEBHOOK_SECRET not set; ignoring webhook.")
            return Response(status=status.HTTP_200_OK)

        raw_body = request.body
        expected = hmac.new(
            webhook_secret.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        event = payload.get("event", "")
        entity = (payload.get("payload", {}).get("payment", {}).get("entity", {}))
        rz_order_id = entity.get("order_id", "")
        rz_payment_id = entity.get("id", "")

        if not rz_order_id:
            return Response(status=status.HTTP_200_OK)

        order = PaymentOrder.objects.select_related("subscription").filter(
            razorpay_order_id=rz_order_id,
        ).first()
        if not order:
            logger.warning("Webhook for unknown order %s", rz_order_id)
            return Response(status=status.HTTP_200_OK)

        if event == "payment.captured" and order.status != PaymentOrder.Status.PAID:
            with transaction.atomic():
                order.razorpay_payment_id = rz_payment_id
                order.status = PaymentOrder.Status.PAID
                order.save(update_fields=["razorpay_payment_id", "status", "updated_at"])

                sub = order.subscription
                if sub.status != UserSubscription.Status.ACTIVE:
                    sub.activate()
                    sub.save()

            notify(
                order.user,
                Notification.NotificationType.PAYMENT_SUCCESS,
                "Payment Successful",
                f"Your payment for '{order.subscription.plan_name}' has been captured. Subscription is active.",
            )

        elif event == "payment.failed" and order.status == PaymentOrder.Status.CREATED:
            reason = entity.get("error_description", "Payment failed")
            order.status = PaymentOrder.Status.FAILED
            order.status_reason = reason[:500]
            order.save(update_fields=["status", "status_reason", "updated_at"])

            notify(
                order.user,
                Notification.NotificationType.PAYMENT_FAILED,
                "Payment Failed",
                f"Your payment for '{order.subscription.plan_name}' failed: {reason[:200]}",
            )

        return Response(status=status.HTTP_200_OK)


RETRY_WINDOW_MINUTES = 30


class RetryPaymentAPIView(APIView):
    """
    Retry a payment that was cancelled or failed within 30 minutes.

    Creates a NEW Razorpay order for the same subscription.
    The old order is marked FAILED.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = str(request.data.get("razorpay_order_id") or "").strip()
        if not order_id:
            return fail("razorpay_order_id is required.")

        order = PaymentOrder.objects.select_related("subscription").filter(
            razorpay_order_id=order_id,
            user=request.user,
        ).first()
        if not order:
            return fail("Payment order not found.", status.HTTP_404_NOT_FOUND)

        if order.status == PaymentOrder.Status.PAID:
            return fail("This payment is already completed.")

        age = timezone.now() - order.created_at
        if age.total_seconds() > RETRY_WINDOW_MINUTES * 60:
            return fail(
                f"Retry window expired. You can only retry within {RETRY_WINDOW_MINUTES} minutes. Please create a new order."
            )

        sub = order.subscription
        if sub.status == UserSubscription.Status.ACTIVE:
            return fail("Subscription is already active.")

        amount_paise = order.amount_paise

        client = _get_razorpay_client()
        try:
            rz_order = client.order.create({
                "amount": amount_paise,
                "currency": "INR",
                "notes": {
                    "plan_id": str(sub.plan_id),
                    "plan_name": sub.plan_name,
                    "user_id": str(request.user.id),
                    "user_email": request.user.email,
                    "retry_of": order_id,
                },
            })
        except Exception as exc:
            logger.error("Razorpay retry order creation failed: %s", exc)
            return fail("Could not create payment order. Please try again.", status.HTTP_502_BAD_GATEWAY)

        with transaction.atomic():
            if order.status != PaymentOrder.Status.PAID:
                order.status = PaymentOrder.Status.FAILED
                order.status_reason = "Replaced by retry"
                order.save(update_fields=["status", "status_reason", "updated_at"])

            PaymentOrder.objects.create(
                user=request.user,
                subscription=sub,
                razorpay_order_id=rz_order["id"],
                amount_paise=amount_paise,
            )

        return ok(
            "New payment order created. Complete the payment in the Razorpay popup.",
            {
                "razorpay_order_id": rz_order["id"],
                "razorpay_key_id": django_settings.RAZORPAY_KEY_ID,
                "amount_paise": amount_paise,
                "currency": "INR",
                "plan_name": sub.plan_name,
                "subscription_id": sub.id,
            },
            status.HTTP_201_CREATED,
        )


class MyPaymentOrdersAPIView(APIView):
    """User can see their payment history including pending/failed ones."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .serializers import PaymentOrderSerializer

        orders = PaymentOrder.objects.filter(user=request.user).order_by("-created_at")
        if request.data.get("status"):
            orders = orders.filter(status=request.data["status"])
        return ok(
            "Payment orders fetched successfully.",
            PaymentOrderSerializer(orders, many=True).data,
            count=orders.count(),
        )
    
    
    


# ==========================================
# BULK HIRING REQUESTS
# ==========================================

class SubmitBulkHiringRequestAPIView(APIView):
    """User submits a request for a large number of workers."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .serializers import BulkHiringRequestSerializer

        pending = BulkHiringRequest.objects.filter(
            user=request.user,
            status=BulkHiringRequest.Status.PENDING,
        ).count()
        if pending >= 3:
            return fail("You already have 3 pending bulk hiring requests. Please wait for them to be reviewed.")

        serializer = BulkHiringRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return fail("Validation error.", errors=serializer.errors)

        bulk_request = serializer.save(user=request.user)
        return ok(
            "Bulk hiring request submitted. Admin will review it shortly.",
            BulkHiringRequestSerializer(bulk_request).data,
            status.HTTP_201_CREATED,
        )


class MyBulkHiringRequestsAPIView(APIView):
    """User sees their own bulk hiring requests."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .serializers import BulkHiringRequestSerializer

        requests_qs = BulkHiringRequest.objects.filter(user=request.user)
        if request.data.get("status"):
            requests_qs = requests_qs.filter(status=request.data["status"])
        return ok(
            "Bulk hiring requests fetched successfully.",
            BulkHiringRequestSerializer(requests_qs, many=True).data,
            count=requests_qs.count(),
        )


class AdminBulkHiringListAPIView(APIView):
    """Admin lists all bulk hiring requests."""

    permission_classes = [IsAdmin]

    def post(self, request):
        from .serializers import AdminBulkHiringRequestSerializer

        requests_qs = BulkHiringRequest.objects.select_related("user", "reviewed_by")
        if request.data.get("status"):
            requests_qs = requests_qs.filter(status=request.data["status"])
        if request.data.get("user_id"):
            requests_qs = requests_qs.filter(user_id=request.data["user_id"])
        return ok(
            "Bulk hiring requests fetched successfully.",
            AdminBulkHiringRequestSerializer(requests_qs, many=True).data,
            count=requests_qs.count(),
        )


class AdminBulkHiringDetailAPIView(APIView):
    """Admin views one bulk hiring request."""

    permission_classes = [IsAdmin]

    def post(self, request):
        from .serializers import AdminBulkHiringRequestSerializer

        bulk_req = BulkHiringRequest.objects.select_related(
            "user", "reviewed_by", "subscription",
        ).filter(id=request.data.get("request_id")).first()
        if not bulk_req:
            return fail("Bulk hiring request not found.", status.HTTP_404_NOT_FOUND)
        return ok(
            "Bulk hiring request fetched successfully.",
            AdminBulkHiringRequestSerializer(bulk_req).data,
        )


class AdminApproveBulkHiringAPIView(APIView):
    """
    Admin approves a bulk hiring request.

    The admin must first create a custom plan, then passes its ID here.
    This endpoint creates and activates a subscription for the user
    and links it to the request.
    """

    permission_classes = [IsAdmin]

    def post(self, request):
        from .serializers import AdminBulkHiringRequestSerializer

        bulk_req = BulkHiringRequest.objects.select_for_update().filter(
            id=request.data.get("request_id"),
            status=BulkHiringRequest.Status.PENDING,
        ).first()
        if not bulk_req:
            return fail("Bulk hiring request not found or already reviewed.", status.HTTP_404_NOT_FOUND)

        plan = SubscriptionPlan.objects.filter(
            id=request.data.get("plan_id"),
            is_active=True,
        ).first()
        if not plan:
            return fail("Plan not found or inactive.", status.HTTP_404_NOT_FOUND)

        note = str(request.data.get("note") or "").strip()
        if len(note) < 5:
            return fail("Please add a note (at least 5 characters).")

        with transaction.atomic():
            subscription = UserSubscription.from_plan(
                bulk_req.user, plan, UserSubscription.Source.ADMIN,
                admin_note=f"Bulk hiring request #{bulk_req.id}: {note}"[:1000],
            )
            subscription.activate(activated_by=request.user)
            subscription.save()

            bulk_req.status = BulkHiringRequest.Status.APPROVED
            bulk_req.admin_note = note[:2000]
            bulk_req.reviewed_by = request.user
            bulk_req.reviewed_at = timezone.now()
            bulk_req.subscription = subscription
            bulk_req.save()

        notify(
            bulk_req.user,
            Notification.NotificationType.BULK_HIRING_APPROVED,
            "Bulk Hiring Approved",
            f"Your bulk hiring request '{bulk_req.title}' has been approved. A subscription has been activated.",
        )
        return ok(
            "Bulk hiring request approved. Subscription activated for the user.",
            AdminBulkHiringRequestSerializer(bulk_req).data,
        )


class AdminRejectBulkHiringAPIView(APIView):
    """Admin rejects a bulk hiring request with a reason."""

    permission_classes = [IsAdmin]

    def post(self, request):
        from .serializers import AdminBulkHiringRequestSerializer

        bulk_req = BulkHiringRequest.objects.filter(
            id=request.data.get("request_id"),
            status=BulkHiringRequest.Status.PENDING,
        ).first()
        if not bulk_req:
            return fail("Bulk hiring request not found or already reviewed.", status.HTTP_404_NOT_FOUND)

        reason = str(request.data.get("reason") or "").strip()
        if len(reason) < 5:
            return fail("Please provide a reason (at least 5 characters).")

        bulk_req.status = BulkHiringRequest.Status.REJECTED
        bulk_req.admin_note = reason[:2000]
        bulk_req.reviewed_by = request.user
        bulk_req.reviewed_at = timezone.now()
        bulk_req.save()

        notify(
            bulk_req.user,
            Notification.NotificationType.BULK_HIRING_REJECTED,
            "Bulk Hiring Rejected",
            f"Your bulk hiring request '{bulk_req.title}' has been rejected. Reason: {reason[:200]}",
        )
        return ok(
            "Bulk hiring request rejected.",
            AdminBulkHiringRequestSerializer(bulk_req).data,
        )
