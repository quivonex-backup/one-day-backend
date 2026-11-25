from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from jobs.models import Job
from applications.models import JobApplication
from subscriptions.models import SubscriptionPlan, UserSubscription
from .models import Notification
from .services import notify

User = get_user_model()


class NotificationServiceTest(TransactionTestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="svc@test.com", password="Test@1234")

    def test_notify_creates_notification(self):
        notify(self.user, Notification.NotificationType.GENERAL, "Hello", "World")
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)
        n = Notification.objects.first()
        self.assertEqual(n.title, "Hello")
        self.assertEqual(n.message, "World")
        self.assertFalse(n.is_read)

    def test_notify_stores_type(self):
        notify(self.user, Notification.NotificationType.PAYMENT_SUCCESS, "Paid", "Done")
        n = Notification.objects.first()
        self.assertEqual(n.notification_type, Notification.NotificationType.PAYMENT_SUCCESS)
        self.assertIsNone(n.job_id)
        self.assertIsNone(n.application_id)


class NotificationAPITestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email="notif@test.com", password="Test@1234")
        cls.other = User.objects.create_user(email="other@test.com", password="Test@1234")
        for i in range(5):
            Notification.objects.create(
                user=cls.user,
                notification_type=Notification.NotificationType.GENERAL,
                title=f"Note {i}",
                message=f"Message {i}",
                is_read=(i < 2),
            )
        Notification.objects.create(
            user=cls.user,
            notification_type=Notification.NotificationType.HIRED,
            title="Hired",
            message="You got hired",
        )
        Notification.objects.create(
            user=cls.other,
            notification_type=Notification.NotificationType.GENERAL,
            title="Other note",
            message="Not yours",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)


class MyNotificationsAPITest(NotificationAPITestBase):
    def test_list_all(self):
        resp = self.client.post("/notifications/my/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["success"])
        self.assertEqual(resp.data["count"], 6)

    def test_filter_by_type(self):
        resp = self.client.post("/notifications/my/", {"type": "HIRED"})
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["data"][0]["notification_type"], "HIRED")

    def test_other_user_not_visible(self):
        resp = self.client.post("/notifications/my/")
        titles = [n["title"] for n in resp.data["data"]]
        self.assertNotIn("Other note", titles)


class UnreadCountAPITest(NotificationAPITestBase):
    def test_unread_count(self):
        resp = self.client.post("/notifications/unread-count/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["unread_count"], 4)


class MarkReadAPITest(NotificationAPITestBase):
    def test_mark_single_read(self):
        n = Notification.objects.filter(user=self.user, is_read=False).first()
        resp = self.client.post("/notifications/mark-read/", {"notification_id": n.id})
        self.assertEqual(resp.status_code, 200)
        n.refresh_from_db()
        self.assertTrue(n.is_read)

    def test_mark_read_missing_id(self):
        resp = self.client.post("/notifications/mark-read/", {})
        self.assertEqual(resp.status_code, 400)

    def test_mark_read_other_user(self):
        n = Notification.objects.filter(user=self.other).first()
        resp = self.client.post("/notifications/mark-read/", {"notification_id": n.id})
        self.assertEqual(resp.status_code, 404)


class MarkAllReadAPITest(NotificationAPITestBase):
    def test_mark_all_read(self):
        resp = self.client.post("/notifications/mark-all-read/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["updated_count"], 4)
        self.assertEqual(Notification.objects.filter(user=self.user, is_read=False).count(), 0)


class UnauthenticatedTest(TestCase):
    def test_unauthenticated(self):
        client = APIClient()
        for url in ["/notifications/my/", "/notifications/unread-count/", "/notifications/mark-read/", "/notifications/mark-all-read/"]:
            resp = client.post(url)
            self.assertEqual(resp.status_code, 401, f"Expected 401 for {url}")
