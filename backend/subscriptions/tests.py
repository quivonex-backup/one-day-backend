import hashlib
import hmac
import json
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from subscriptions.models import PaymentOrder, SubscriptionPlan, UserSubscription

FAKE_RZ_KEY = "rzp_test_fake123"
FAKE_RZ_SECRET = "fakesecret456"
FAKE_WEBHOOK_SECRET = "whsec_test789"


User = get_user_model()


class SubscriptionTestBase(APITestCase):
    """Shared users, plans and helpers for subscription tests."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com", mobile_number="9500000001", password="TestPassword123!",
        )
        self.other = User.objects.create_user(
            email="other@example.com", mobile_number="9500000002", password="TestPassword123!",
        )
        self.admin = User.objects.create_superuser(
            email="admin@example.com", mobile_number="9500000003", password="TestPassword123!",
        )
        self.free_plan = self.make_plan(name="Starter", price="0.00", job_post_limit=1, max_vacancies_per_job=2)
        self.basic_plan = self.make_plan(name="Basic", price="499.00", job_post_limit=5, max_vacancies_per_job=10)

    def make_plan(self, **changes):
        data = {
            "name": "Plan",
            "price": "199.00",
            "validity_days": 30,
            "job_post_limit": 3,
            "max_vacancies_per_job": 5,
        }
        data.update(changes)
        return SubscriptionPlan.objects.create(**data)

    def give_subscription(self, user, plan, days_left=10, jobs_used=0):
        sub = UserSubscription.from_plan(user, plan, UserSubscription.Source.ADMIN)
        sub.activate()
        sub.ends_at = timezone.now() + timedelta(days=days_left)
        sub.jobs_used = jobs_used
        sub.save()
        return sub

    def login(self, user):
        if user is None:
            self.client.credentials()
        else:
            token = RefreshToken.for_user(user).access_token
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def post(self, url, body=None, user=None):
        self.login(user)
        return self.client.post(url, body or {}, format="json")


class PublicPlanTests(SubscriptionTestBase):

    def test_anyone_can_see_active_public_plans(self):
        self.make_plan(name="Hidden", is_active=False)
        self.make_plan(name="Custom Bulk", is_custom=True)

        response = self.post("/subscriptions/plans/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in response.data["data"]]
        self.assertEqual(names, ["Starter", "Basic"])
        self.assertTrue(response.data["data"][0]["is_free"])

    def test_plan_detail_hides_inactive_and_custom(self):
        custom = self.make_plan(name="Custom Bulk", is_custom=True)
        self.assertEqual(self.post("/subscriptions/plans/detail/", {"plan_id": custom.id}).status_code, 404)
        self.assertEqual(self.post("/subscriptions/plans/detail/", {"plan_id": self.basic_plan.id}).status_code, 200)


class FreePlanTests(SubscriptionTestBase):

    def test_user_can_activate_free_plan_once(self):
        response = self.post("/subscriptions/activate-free/", {"plan_id": self.free_plan.id}, self.user)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["data"]["status"], UserSubscription.Status.ACTIVE)
        self.assertEqual(response.data["data"]["jobs_remaining"], 1)

        response = self.post("/subscriptions/activate-free/", {"plan_id": self.free_plan.id}, self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(UserSubscription.objects.filter(user=self.user).count(), 1)

    def test_only_one_free_plan_even_if_admin_adds_another(self):
        second_free = self.make_plan(name="Festival Free", price="0.00")
        self.post("/subscriptions/activate-free/", {"plan_id": self.free_plan.id}, self.user)

        response = self.post("/subscriptions/activate-free/", {"plan_id": second_free.id}, self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_paid_plan_cannot_be_activated_as_free(self):
        response = self.post("/subscriptions/activate-free/", {"plan_id": self.basic_plan.id}, self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(UserSubscription.objects.exists())

    def test_free_plan_needs_login(self):
        response = self.post("/subscriptions/activate-free/", {"plan_id": self.free_plan.id})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MySubscriptionTests(SubscriptionTestBase):

    def test_summary_adds_up_active_subscriptions(self):
        self.give_subscription(self.user, self.free_plan)
        self.give_subscription(self.user, self.basic_plan, jobs_used=2)
        self.give_subscription(self.user, self.basic_plan, days_left=-1)
        self.give_subscription(self.other, self.basic_plan)

        response = self.post("/subscriptions/my/", {}, self.user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 3)
        summary = response.data["summary"]
        self.assertTrue(summary["can_post_job"])
        self.assertEqual(summary["jobs_remaining"], 4)
        self.assertEqual(summary["max_vacancies_per_job"], 10)

    def test_active_only_hides_expired_and_cancelled(self):
        self.give_subscription(self.user, self.basic_plan, days_left=-1)
        cancelled = self.give_subscription(self.user, self.basic_plan)
        cancelled.status = UserSubscription.Status.CANCELLED
        cancelled.save()

        response = self.post("/subscriptions/my/", {"active_only": True}, self.user)

        self.assertEqual(response.data["data"], [])
        self.assertFalse(response.data["summary"]["can_post_job"])

    def test_plan_changes_do_not_change_bought_subscription(self):
        sub = self.give_subscription(self.user, self.basic_plan)
        self.post("/subscriptions/admin/plans/update/", {"plan_id": self.basic_plan.id, "job_post_limit": 50}, self.admin)

        sub.refresh_from_db()
        self.assertEqual(sub.job_post_limit, 5)


class AdminPlanTests(SubscriptionTestBase):

    def plan_body(self, **changes):
        body = {
            "name": "Business",
            "description": "For contractors",
            "price": "1999.00",
            "validity_days": 90,
            "job_post_limit": 20,
            "max_vacancies_per_job": 50,
            "featured_jobs_included": 5,
        }
        body.update(changes)
        return body

    def test_admin_creates_plan(self):
        response = self.post("/subscriptions/admin/plans/create/", self.plan_body(), self.admin)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(SubscriptionPlan.objects.get(name="Business").created_by, self.admin)

    def test_normal_user_cannot_manage_plans(self):
        for url in ("/subscriptions/admin/plans/create/", "/subscriptions/admin/plans/",
                    "/subscriptions/admin/plans/update/", "/subscriptions/admin/plans/set-active/"):
            response = self.post(url, self.plan_body(plan_id=self.basic_plan.id), self.user)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, url)

    def test_plan_validation(self):
        bad_bodies = [
            self.plan_body(price="-1"),
            self.plan_body(validity_days=0),
            self.plan_body(job_post_limit=0),
            self.plan_body(max_vacancies_per_job=0),
            self.plan_body(featured_jobs_included=99),
            self.plan_body(name="basic"),
        ]
        for body in bad_bodies:
            response = self.post("/subscriptions/admin/plans/create/", body, self.admin)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, body)

    def test_admin_can_hide_plan(self):
        response = self.post(
            "/subscriptions/admin/plans/set-active/", {"plan_id": self.basic_plan.id, "is_active": False}, self.admin,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in self.post("/subscriptions/plans/").data["data"]]
        self.assertNotIn("Basic", names)

    def test_admin_list_includes_inactive_and_custom(self):
        self.make_plan(name="Hidden", is_active=False)
        self.make_plan(name="Custom Bulk", is_custom=True)
        response = self.post("/subscriptions/admin/plans/", {}, self.admin)
        self.assertEqual(response.data["count"], 4)


class AdminSubscriptionTests(SubscriptionTestBase):

    def test_admin_activates_plan_for_offline_payment(self):
        response = self.post(
            "/subscriptions/admin/subscriptions/activate/",
            {"user_id": self.user.id, "plan_id": self.basic_plan.id, "note": "Paid Rs 499 by UPI"},
            self.admin,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        sub = UserSubscription.objects.get(user=self.user)
        self.assertEqual(sub.source, UserSubscription.Source.ADMIN)
        self.assertEqual(sub.activated_by, self.admin)
        self.assertTrue(sub.is_currently_active)

    def test_admin_can_give_custom_plan(self):
        custom = self.make_plan(name="Site 100 workers", is_custom=True, max_vacancies_per_job=100)
        response = self.post(
            "/subscriptions/admin/subscriptions/activate/",
            {"user_id": self.user.id, "plan_id": custom.id, "note": "Bulk request approved"},
            self.admin,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_manual_activation_needs_note(self):
        response = self.post(
            "/subscriptions/admin/subscriptions/activate/",
            {"user_id": self.user.id, "plan_id": self.basic_plan.id},
            self.admin,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_normal_user_cannot_activate_or_cancel(self):
        response = self.post(
            "/subscriptions/admin/subscriptions/activate/",
            {"user_id": self.user.id, "plan_id": self.basic_plan.id, "note": "I paid, trust me"},
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(UserSubscription.objects.exists())

        sub = self.give_subscription(self.other, self.basic_plan)
        response = self.post(
            "/subscriptions/admin/subscriptions/cancel/", {"subscription_id": sub.id, "note": "cancel it"}, self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cancels_subscription(self):
        sub = self.give_subscription(self.user, self.basic_plan)
        response = self.post(
            "/subscriptions/admin/subscriptions/cancel/",
            {"subscription_id": sub.id, "note": "Payment bounced"},
            self.admin,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        sub.refresh_from_db()
        self.assertEqual(sub.status, UserSubscription.Status.CANCELLED)
        self.assertFalse(self.post("/subscriptions/my/", {}, self.user).data["summary"]["can_post_job"])

    def test_user_sees_only_own_subscriptions(self):
        self.give_subscription(self.other, self.basic_plan)
        response = self.post("/subscriptions/my/", {}, self.user)
        self.assertEqual(response.data["data"], [])


@override_settings(
    RAZORPAY_KEY_ID=FAKE_RZ_KEY,
    RAZORPAY_KEY_SECRET=FAKE_RZ_SECRET,
    RAZORPAY_WEBHOOK_SECRET=FAKE_WEBHOOK_SECRET,
)
class RazorpayPaymentTests(SubscriptionTestBase):

    FAKE_ORDER_ID = "order_Test123abc"
    FAKE_PAYMENT_ID = "pay_Test456def"

    def _valid_signature(self, order_id, payment_id):
        return hmac.new(
            FAKE_RZ_SECRET.encode(),
            f"{order_id}|{payment_id}".encode(),
            hashlib.sha256,
        ).hexdigest()

    def _webhook_signature(self, body_bytes):
        return hmac.new(
            FAKE_WEBHOOK_SECRET.encode(),
            body_bytes,
            hashlib.sha256,
        ).hexdigest()

    @patch("subscriptions.views._get_razorpay_client")
    def test_create_order_success(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client.order.create.return_value = {"id": self.FAKE_ORDER_ID}
        mock_client_fn.return_value = mock_client

        response = self.post(
            "/subscriptions/payment/create-order/",
            {"plan_id": self.basic_plan.id},
            self.user,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["data"]["razorpay_order_id"], self.FAKE_ORDER_ID)
        self.assertEqual(response.data["data"]["razorpay_key_id"], FAKE_RZ_KEY)
        self.assertEqual(response.data["data"]["amount_paise"], 49900)

        order = PaymentOrder.objects.get(razorpay_order_id=self.FAKE_ORDER_ID)
        self.assertEqual(order.status, PaymentOrder.Status.CREATED)
        self.assertEqual(order.subscription.status, UserSubscription.Status.PENDING_PAYMENT)

    @patch("subscriptions.views._get_razorpay_client")
    def test_create_order_rejects_free_plan(self, mock_client_fn):
        response = self.post(
            "/subscriptions/payment/create-order/",
            {"plan_id": self.free_plan.id},
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_client_fn.assert_not_called()

    @patch("subscriptions.views._get_razorpay_client")
    def test_create_order_needs_login(self, mock_client_fn):
        response = self.post("/subscriptions/payment/create-order/", {"plan_id": self.basic_plan.id})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("subscriptions.views._get_razorpay_client")
    def test_verify_payment_activates_subscription(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client.order.create.return_value = {"id": self.FAKE_ORDER_ID}
        mock_client_fn.return_value = mock_client

        self.post("/subscriptions/payment/create-order/", {"plan_id": self.basic_plan.id}, self.user)

        sig = self._valid_signature(self.FAKE_ORDER_ID, self.FAKE_PAYMENT_ID)
        response = self.post("/subscriptions/payment/verify/", {
            "razorpay_order_id": self.FAKE_ORDER_ID,
            "razorpay_payment_id": self.FAKE_PAYMENT_ID,
            "razorpay_signature": sig,
        }, self.user)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order = PaymentOrder.objects.get(razorpay_order_id=self.FAKE_ORDER_ID)
        self.assertEqual(order.status, PaymentOrder.Status.PAID)
        self.assertEqual(order.subscription.status, UserSubscription.Status.ACTIVE)
        self.assertTrue(order.subscription.is_currently_active)

    @patch("subscriptions.views._get_razorpay_client")
    def test_verify_bad_signature_fails(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client.order.create.return_value = {"id": self.FAKE_ORDER_ID}
        mock_client_fn.return_value = mock_client

        self.post("/subscriptions/payment/create-order/", {"plan_id": self.basic_plan.id}, self.user)

        response = self.post("/subscriptions/payment/verify/", {
            "razorpay_order_id": self.FAKE_ORDER_ID,
            "razorpay_payment_id": self.FAKE_PAYMENT_ID,
            "razorpay_signature": "bad_signature",
        }, self.user)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        order = PaymentOrder.objects.get(razorpay_order_id=self.FAKE_ORDER_ID)
        self.assertEqual(order.status, PaymentOrder.Status.FAILED)

    @patch("subscriptions.views._get_razorpay_client")
    def test_verify_idempotent(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client.order.create.return_value = {"id": self.FAKE_ORDER_ID}
        mock_client_fn.return_value = mock_client

        self.post("/subscriptions/payment/create-order/", {"plan_id": self.basic_plan.id}, self.user)
        sig = self._valid_signature(self.FAKE_ORDER_ID, self.FAKE_PAYMENT_ID)
        self.post("/subscriptions/payment/verify/", {
            "razorpay_order_id": self.FAKE_ORDER_ID,
            "razorpay_payment_id": self.FAKE_PAYMENT_ID,
            "razorpay_signature": sig,
        }, self.user)

        response = self.post("/subscriptions/payment/verify/", {
            "razorpay_order_id": self.FAKE_ORDER_ID,
            "razorpay_payment_id": self.FAKE_PAYMENT_ID,
            "razorpay_signature": sig,
        }, self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(PaymentOrder.objects.count(), 1)

    @patch("subscriptions.views._get_razorpay_client")
    def test_other_user_cannot_verify(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client.order.create.return_value = {"id": self.FAKE_ORDER_ID}
        mock_client_fn.return_value = mock_client

        self.post("/subscriptions/payment/create-order/", {"plan_id": self.basic_plan.id}, self.user)
        sig = self._valid_signature(self.FAKE_ORDER_ID, self.FAKE_PAYMENT_ID)
        response = self.post("/subscriptions/payment/verify/", {
            "razorpay_order_id": self.FAKE_ORDER_ID,
            "razorpay_payment_id": self.FAKE_PAYMENT_ID,
            "razorpay_signature": sig,
        }, self.other)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("subscriptions.views._get_razorpay_client")
    def test_webhook_captured_activates_subscription(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client.order.create.return_value = {"id": self.FAKE_ORDER_ID}
        mock_client_fn.return_value = mock_client

        self.post("/subscriptions/payment/create-order/", {"plan_id": self.basic_plan.id}, self.user)

        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": self.FAKE_PAYMENT_ID,
                        "order_id": self.FAKE_ORDER_ID,
                    }
                }
            },
        }
        body = json.dumps(payload).encode()
        sig = self._webhook_signature(body)

        response = self.client.post(
            "/subscriptions/payment/razorpay/webhook/",
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order = PaymentOrder.objects.get(razorpay_order_id=self.FAKE_ORDER_ID)
        self.assertEqual(order.status, PaymentOrder.Status.PAID)
        self.assertEqual(order.subscription.status, UserSubscription.Status.ACTIVE)

    @patch("subscriptions.views._get_razorpay_client")
    def test_webhook_bad_signature_rejected(self, mock_client_fn):
        payload = json.dumps({"event": "payment.captured", "payload": {}}).encode()
        response = self.client.post(
            "/subscriptions/payment/razorpay/webhook/",
            data=payload,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE="invalid",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("subscriptions.views._get_razorpay_client")
    def test_webhook_failed_marks_order(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client.order.create.return_value = {"id": self.FAKE_ORDER_ID}
        mock_client_fn.return_value = mock_client

        self.post("/subscriptions/payment/create-order/", {"plan_id": self.basic_plan.id}, self.user)

        payload = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": self.FAKE_PAYMENT_ID,
                        "order_id": self.FAKE_ORDER_ID,
                        "error_description": "Card declined",
                    }
                }
            },
        }
        body = json.dumps(payload).encode()
        sig = self._webhook_signature(body)

        response = self.client.post(
            "/subscriptions/payment/razorpay/webhook/",
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order = PaymentOrder.objects.get(razorpay_order_id=self.FAKE_ORDER_ID)
        self.assertEqual(order.status, PaymentOrder.Status.FAILED)
        self.assertIn("Card declined", order.status_reason)
        
        
        
class RetryPaymentTests(SubscriptionTestBase):

    FAKE_ORDER_ID = "order_original123"
    FAKE_RETRY_ORDER_ID = "order_retry456"

    def _create_pending_order(self, age_minutes=5):
        sub = UserSubscription.from_plan(self.user, self.basic_plan, UserSubscription.Source.RAZORPAY)
        sub.save()
        order = PaymentOrder.objects.create(
            user=self.user,
            subscription=sub,
            razorpay_order_id=self.FAKE_ORDER_ID,
            amount_paise=49900,
        )
        if age_minutes:
            PaymentOrder.objects.filter(pk=order.pk).update(
                created_at=timezone.now() - timedelta(minutes=age_minutes),
            )
            order.refresh_from_db()
        return order, sub

    @patch("subscriptions.views._get_razorpay_client")
    def test_retry_within_window(self, mock_client):
        mock_client.return_value.order.create.return_value = {"id": self.FAKE_RETRY_ORDER_ID}
        order, sub = self._create_pending_order(age_minutes=10)
        self.login(self.user)
        resp = self.client.post("/subscriptions/payment/retry/", {"razorpay_order_id": self.FAKE_ORDER_ID})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["data"]["razorpay_order_id"], self.FAKE_RETRY_ORDER_ID)
        order.refresh_from_db()
        self.assertEqual(order.status, PaymentOrder.Status.FAILED)
        self.assertEqual(PaymentOrder.objects.filter(subscription=sub).count(), 2)

    def test_retry_expired_window(self):
        self._create_pending_order(age_minutes=35)
        self.login(self.user)
        resp = self.client.post("/subscriptions/payment/retry/", {"razorpay_order_id": self.FAKE_ORDER_ID})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Retry window expired", resp.data["message"])

    def test_retry_already_paid(self):
        order, sub = self._create_pending_order(age_minutes=5)
        order.status = PaymentOrder.Status.PAID
        order.save(update_fields=["status"])
        sub.activate()
        sub.save()
        self.login(self.user)
        resp = self.client.post("/subscriptions/payment/retry/", {"razorpay_order_id": self.FAKE_ORDER_ID})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already completed", resp.data["message"])

    def test_retry_other_user_blocked(self):
        self._create_pending_order(age_minutes=5)
        self.login(self.other)
        resp = self.client.post("/subscriptions/payment/retry/", {"razorpay_order_id": self.FAKE_ORDER_ID})
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class ExpireStaleOrdersTests(SubscriptionTestBase):

    def call_command(self, *args):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command("expire_stale_orders", *args, stdout=out)
        return out.getvalue()

    def test_expires_old_created_orders(self):
        sub = UserSubscription.from_plan(self.user, self.basic_plan, UserSubscription.Source.RAZORPAY)
        sub.save()
        order = PaymentOrder.objects.create(
            user=self.user, subscription=sub, razorpay_order_id="order_stale1", amount_paise=49900,
        )
        PaymentOrder.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(minutes=35))
        output = self.call_command()
        order.refresh_from_db()
        sub.refresh_from_db()
        self.assertEqual(order.status, PaymentOrder.Status.FAILED)
        self.assertEqual(sub.status, UserSubscription.Status.CANCELLED)
        self.assertIn("1 stale order(s) expired", output)

    def test_skips_recent_orders(self):
        sub = UserSubscription.from_plan(self.user, self.basic_plan, UserSubscription.Source.RAZORPAY)
        sub.save()
        PaymentOrder.objects.create(
            user=self.user, subscription=sub, razorpay_order_id="order_fresh1", amount_paise=49900,
        )
        output = self.call_command()
        self.assertIn("0 stale order(s) expired", output)

    def test_dry_run(self):
        sub = UserSubscription.from_plan(self.user, self.basic_plan, UserSubscription.Source.RAZORPAY)
        sub.save()
        order = PaymentOrder.objects.create(
            user=self.user, subscription=sub, razorpay_order_id="order_dry1", amount_paise=49900,
        )
        PaymentOrder.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(minutes=35))
        output = self.call_command("--dry-run")
        order.refresh_from_db()
        self.assertEqual(order.status, PaymentOrder.Status.CREATED)
        self.assertIn("DRY RUN", output)


class MyPaymentOrdersTests(SubscriptionTestBase):

    def test_list_own_orders(self):
        sub = UserSubscription.from_plan(self.user, self.basic_plan, UserSubscription.Source.RAZORPAY)
        sub.save()
        PaymentOrder.objects.create(user=self.user, subscription=sub, razorpay_order_id="order_a", amount_paise=49900)
        PaymentOrder.objects.create(user=self.user, subscription=sub, razorpay_order_id="order_b", amount_paise=49900)
        self.login(self.user)
        resp = self.client.post("/subscriptions/payment/my-orders/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 2)

    def test_other_user_sees_nothing(self):
        sub = UserSubscription.from_plan(self.user, self.basic_plan, UserSubscription.Source.RAZORPAY)
        sub.save()
        PaymentOrder.objects.create(user=self.user, subscription=sub, razorpay_order_id="order_c", amount_paise=49900)
        self.login(self.other)
        resp = self.client.post("/subscriptions/payment/my-orders/")
        self.assertEqual(resp.data["count"], 0)