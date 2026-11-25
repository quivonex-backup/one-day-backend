from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from applications.models import JobApplication
from common.models import JobCategory, JobSubCategory, PostalLocation
from jobs.models import Job
from notifications.models import Notification
from subscriptions.models import SubscriptionPlan, UserSubscription
from .models import Review

User = get_user_model()


class ReviewTestBase(APITestCase):

    def setUp(self):
        self.poster = User.objects.create_user(email="poster@test.com", password="Test@1234")
        self.applicant = User.objects.create_user(email="applicant@test.com", password="Test@1234")
        self.outsider = User.objects.create_user(email="outsider@test.com", password="Test@1234")

        loc = PostalLocation.objects.create(
            pincode="415001", post_office="Satara H.O",
            district_name="SATARA", state_name="MAHARASHTRA",
        )
        cat = JobCategory.objects.create(name="Construction")
        sub_cat = JobSubCategory.objects.create(category=cat, name="Mason")

        plan = SubscriptionPlan.objects.create(
            name="Test", price=0, validity_days=365,
            job_post_limit=100, max_vacancies_per_job=100,
        )
        for u in (self.poster, self.applicant):
            s = UserSubscription.from_plan(u, plan, UserSubscription.Source.FREE)
            s.activate()
            s.save()

        today = timezone.localdate()
        self.job = Job.objects.create(
            posted_by=self.poster, status=Job.Status.PUBLISHED,
            job_title="Mason Helper", job_category=cat, job_subcategory=sub_cat,
            job_duration="ONE_DAY", job_description="Need help",
            salary_type="DAILY", daily_wage=700,
            address="Main Road", postal_location=loc,
            start_time="08:00", end_time="17:00",
            job_start_date=today + timedelta(days=5),
            job_end_date=today + timedelta(days=5),
            application_deadline=today + timedelta(days=3),
        )

        self.application = JobApplication.objects.create(
            job=self.job, applicant=self.applicant, status=JobApplication.Status.COMPLETED,
        )

    def login(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


class CreateReviewTests(ReviewTestBase):

    def test_applicant_can_review_poster(self):
        self.login(self.applicant)
        resp = self.client.post("/reviews/create/", {"application": self.application.id, "rating": 5, "comment": "Great job!"})
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data["success"])
        self.assertEqual(resp.data["data"]["review_type"], Review.ReviewType.APPLICANT_TO_POSTER)

    def test_poster_can_review_applicant(self):
        self.login(self.poster)
        resp = self.client.post("/reviews/create/", {"application": self.application.id, "rating": 4})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["data"]["review_type"], Review.ReviewType.POSTER_TO_APPLICANT)

    def test_cannot_review_non_completed_application(self):
        self.application.status = JobApplication.Status.HIRED
        self.application.save(update_fields=["status"])
        self.login(self.applicant)
        resp = self.client.post("/reviews/create/", {"application": self.application.id, "rating": 5})
        self.assertEqual(resp.status_code, 400)

    def test_outsider_cannot_review(self):
        self.login(self.outsider)
        resp = self.client.post("/reviews/create/", {"application": self.application.id, "rating": 5})
        self.assertEqual(resp.status_code, 400)

    def test_duplicate_review_blocked(self):
        self.login(self.applicant)
        self.client.post("/reviews/create/", {"application": self.application.id, "rating": 5})
        resp = self.client.post("/reviews/create/", {"application": self.application.id, "rating": 4})
        self.assertEqual(resp.status_code, 400)

    def test_invalid_rating_rejected(self):
        self.login(self.applicant)
        resp = self.client.post("/reviews/create/", {"application": self.application.id, "rating": 6})
        self.assertEqual(resp.status_code, 400)

    def test_rating_zero_rejected(self):
        self.login(self.applicant)
        resp = self.client.post("/reviews/create/", {"application": self.application.id, "rating": 0})
        self.assertEqual(resp.status_code, 400)

    def test_unauthenticated_cannot_review(self):
        resp = self.client.post("/reviews/create/", {"application": self.application.id, "rating": 5})
        self.assertEqual(resp.status_code, 401)


class ReviewNotificationTest(TransactionTestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        self.client = APIClient()
        self.poster = User.objects.create_user(email="poster2@test.com", password="Test@1234")
        self.applicant = User.objects.create_user(email="applicant2@test.com", password="Test@1234")
        loc = PostalLocation.objects.create(pincode="415002", post_office="Test", district_name="TEST", state_name="TEST")
        cat = JobCategory.objects.create(name="IT")
        sub_cat = JobSubCategory.objects.create(category=cat, name="Dev")
        plan = SubscriptionPlan.objects.create(name="T", price=0, validity_days=365, job_post_limit=100, max_vacancies_per_job=100)
        for u in (self.poster, self.applicant):
            s = UserSubscription.from_plan(u, plan, UserSubscription.Source.FREE)
            s.activate()
            s.save()
        today = timezone.localdate()
        self.job = Job.objects.create(
            posted_by=self.poster, status=Job.Status.PUBLISHED, job_title="Dev", job_category=cat, job_subcategory=sub_cat,
            job_duration="ONE_DAY", job_description="x", salary_type="DAILY", daily_wage=700,
            address="x", postal_location=loc, start_time="08:00", end_time="17:00",
            job_start_date=today + timedelta(days=5), job_end_date=today + timedelta(days=5),
            application_deadline=today + timedelta(days=3),
        )
        self.application = JobApplication.objects.create(job=self.job, applicant=self.applicant, status=JobApplication.Status.COMPLETED)
        token = RefreshToken.for_user(self.applicant).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_review_sends_notification(self):
        self.client.post("/reviews/create/", {"application": self.application.id, "rating": 5})
        self.assertTrue(Notification.objects.filter(user=self.poster, title="New Review").exists())


class ReviewListTests(ReviewTestBase):

    def test_list_own_reviews(self):
        Review.objects.create(application=self.application, reviewer=self.applicant, review_type=Review.ReviewType.APPLICANT_TO_POSTER, rating=5)
        self.login(self.applicant)
        resp = self.client.post("/reviews/my/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)

    def test_poster_sees_reviews_on_their_jobs(self):
        Review.objects.create(application=self.application, reviewer=self.applicant, review_type=Review.ReviewType.APPLICANT_TO_POSTER, rating=4)
        self.login(self.poster)
        resp = self.client.post("/reviews/my/")
        self.assertEqual(resp.data["count"], 1)

    def test_outsider_sees_nothing(self):
        Review.objects.create(application=self.application, reviewer=self.applicant, review_type=Review.ReviewType.APPLICANT_TO_POSTER, rating=5)
        self.login(self.outsider)
        resp = self.client.post("/reviews/my/")
        self.assertEqual(resp.data["count"], 0)


class ReviewDetailTests(ReviewTestBase):

    def test_detail_by_id(self):
        r = Review.objects.create(application=self.application, reviewer=self.applicant, review_type=Review.ReviewType.APPLICANT_TO_POSTER, rating=5)
        self.login(self.applicant)
        resp = self.client.post("/reviews/detail/", {"review_id": r.id})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["data"]["rating"], 5)

    def test_outsider_cannot_see_detail(self):
        r = Review.objects.create(application=self.application, reviewer=self.applicant, review_type=Review.ReviewType.APPLICANT_TO_POSTER, rating=5)
        self.login(self.outsider)
        resp = self.client.post("/reviews/detail/", {"review_id": r.id})
        self.assertEqual(resp.status_code, 404)


class UserRatingSummaryTests(ReviewTestBase):

    def test_average_rating(self):
        app2 = JobApplication.objects.create(job=self.job, applicant=self.outsider, status=JobApplication.Status.COMPLETED)
        Review.objects.create(application=self.application, reviewer=self.applicant, review_type=Review.ReviewType.APPLICANT_TO_POSTER, rating=4)
        Review.objects.create(application=app2, reviewer=self.outsider, review_type=Review.ReviewType.APPLICANT_TO_POSTER, rating=2)
        resp = self.client.post("/reviews/user-rating/", {"user_id": self.poster.id})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["data"]["average_rating"], 3.0)
        self.assertEqual(resp.data["data"]["total_reviews"], 2)

    def test_no_reviews_returns_null(self):
        resp = self.client.post("/reviews/user-rating/", {"user_id": self.poster.id})
        self.assertEqual(resp.data["data"]["average_rating"], None)
        self.assertEqual(resp.data["data"]["total_reviews"], 0)

    def test_missing_user_id(self):
        resp = self.client.post("/reviews/user-rating/", {})
        self.assertEqual(resp.status_code, 400)

    def test_applicant_rating_as_worker(self):
        Review.objects.create(application=self.application, reviewer=self.poster, review_type=Review.ReviewType.POSTER_TO_APPLICANT, rating=5)
        resp = self.client.post("/reviews/user-rating/", {"user_id": self.applicant.id})
        self.assertEqual(resp.data["data"]["average_rating"], 5.0)
        self.assertEqual(resp.data["data"]["total_reviews"], 1)