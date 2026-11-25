from datetime import timedelta

from django.utils import timezone
from rest_framework import status

from subscriptions.models import SubscriptionPlan, UserSubscription
from .tests import JobTestBase


class JobPostingSubscriptionTests(JobTestBase):
    """Creating a job requires an active subscription with remaining credits."""

    def setUp(self):
        super().setUp()
        # Remove the generous test subscriptions from JobTestBase so we
        # can test enforcement with tight limits.
        UserSubscription.objects.all().delete()
        self.plan = SubscriptionPlan.objects.create(
            name="Basic", price="499.00", validity_days=30,
            job_post_limit=2, max_vacancies_per_job=5,
        )

    def give_subscription(self, user, plan=None, days_left=10, jobs_used=0, **extra):
        plan = plan or self.plan
        sub = UserSubscription.from_plan(user, plan, UserSubscription.Source.ADMIN)
        sub.activate()
        sub.ends_at = timezone.now() + timedelta(days=days_left)
        sub.jobs_used = jobs_used
        sub.save()
        return sub

    def test_no_subscription_blocks_job_creation(self):
        self.login(self.owner)
        response = self.client.post("/jobs/create/", self.payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("subscription", response.data["message"].lower())

    def test_active_subscription_allows_job_creation(self):
        self.give_subscription(self.owner)
        self.login(self.owner)
        response = self.client.post("/jobs/create/", self.payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_job_credit_consumed_on_create(self):
        sub = self.give_subscription(self.owner)
        self.login(self.owner)
        self.client.post("/jobs/create/", self.payload(), format="json")
        sub.refresh_from_db()
        self.assertEqual(sub.jobs_used, 1)

    def test_exhausted_credits_block_creation(self):
        self.give_subscription(self.owner, jobs_used=2)
        self.login(self.owner)
        response = self.client.post("/jobs/create/", self.payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_expired_subscription_blocks_creation(self):
        self.give_subscription(self.owner, days_left=-1)
        self.login(self.owner)
        response = self.client.post("/jobs/create/", self.payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_vacancies_over_plan_limit_rejected(self):
        self.give_subscription(self.owner)
        self.login(self.owner)
        response = self.client.post(
            "/jobs/create/",
            self.payload(number_of_vacancies=50),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("vacancies", response.data["message"].lower())

    def test_edit_after_rejection_is_free(self):
        sub = self.give_subscription(self.owner, jobs_used=1)
        job = self.make_job(owner=self.owner, status_value="REJECTED")
        self.login(self.owner)
        response = self.client.post(
            "/jobs/update/",
            {"id": job.id, "job_title": "Updated Title"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        sub.refresh_from_db()
        self.assertEqual(sub.jobs_used, 1)

    def test_credit_uses_soonest_expiring_subscription(self):
        soon = self.give_subscription(self.owner, days_left=3)
        later = self.give_subscription(self.owner, days_left=30)
        self.login(self.owner)
        self.client.post("/jobs/create/", self.payload(), format="json")
        soon.refresh_from_db()
        later.refresh_from_db()
        self.assertEqual(soon.jobs_used, 1)
        self.assertEqual(later.jobs_used, 0)