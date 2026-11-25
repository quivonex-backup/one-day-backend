from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import UserProfile
from applications.models import JobApplication
from common.models import EmploymentType, JobCategory, JobSubCategory, PostalLocation
from jobs.models import Job


User = get_user_model()


class UnifiedUserFlowTests(APITestCase):
    def setUp(self):
        self.poster = User.objects.create_user(
            email="poster@example.com",
            mobile_number="9000000001",
            password="TestPassword123!",
            is_email_verified=True,
        )
        self.applicant = User.objects.create_user(
            email="applicant@example.com",
            mobile_number="9000000002",
            password="TestPassword123!",
            is_email_verified=True,
        )
        UserProfile.objects.create(user=self.poster, full_name="Job Poster")
        UserProfile.objects.create(user=self.applicant, full_name="Job Applicant")
        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            mobile_number="9000000003",
            password="TestPassword123!",
        )
        self.postal_location = PostalLocation.objects.create(
            pincode="415001",
            post_office="Satara H.O",
            district_name="SATARA",
            state_name="MAHARASHTRA",
        )
        self.category = JobCategory.objects.create(name="Technology")
        self.subcategory = JobSubCategory.objects.create(category=self.category, name="Backend Development")
        self.employment_type = EmploymentType.objects.create(name="Full Time")

    def authenticate(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")

    def job_payload(self):
        today = timezone.now().date()
        return {
            "job_title": "Python Developer",
            "job_category": self.category.pk,
            "job_subcategory": self.subcategory.pk,
            "employment_type": self.employment_type.pk,
            "job_duration": "ONE_DAY",
            "job_description": "Build and maintain Django API endpoints for customers.",
            "salary_type": "DAILY",
            "daily_wage": "1200.00",
            "number_of_vacancies": 1,
            "address": "Satara office",
            "postal_location_id": self.postal_location.pk,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "job_start_date": str(today + timedelta(days=3)),
            "job_end_date": str(today + timedelta(days=3)),
            "application_deadline": str(today + timedelta(days=2)),
        }

    def make_job(self, status_value):
        today = timezone.now().date()
        return Job.objects.create(
            posted_by=self.poster,
            status=status_value,
            job_title="Python Developer",
            job_category=self.category,
            job_subcategory=self.subcategory,
            employment_type=self.employment_type,
            job_duration="ONE_DAY",
            job_description="Build and maintain Django API endpoints for customers.",
            salary_type="DAILY",
            daily_wage=1200,
            address="Satara office",
            postal_location=self.postal_location,
            start_time="09:00:00",
            end_time="17:00:00",
            job_start_date=today + timedelta(days=3),
            job_end_date=today + timedelta(days=3),
            application_deadline=today + timedelta(days=2),
        )

    def test_register_and_login_have_no_role_field(self):
        response = self.client.post("/accounts/register/", {
            "full_name": "Normal User",
            "email": "normal@example.com",
            "mobile_number": "9000000004",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        user = User.objects.get(email="normal@example.com")
        self.assertTrue(UserProfile.objects.filter(user=user, full_name="Normal User").exists())
        self.assertFalse(hasattr(user, "role"))

        response = self.client.post("/accounts/login/", {
            "email": self.poster.email,
            "password": "TestPassword123!",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertNotIn("role", response.data["user"])
        self.assertFalse(response.data["user"]["is_admin"])

    def test_one_user_posts_and_another_user_applies(self):
        self.authenticate(self.poster)
        response = self.client.post("/jobs/create/", self.job_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        job = Job.objects.get(pk=response.data["data"]["id"])
        self.assertEqual(job.posted_by, self.poster)
        self.assertEqual(job.status, Job.Status.PENDING_APPROVAL)

        # Location text is auto-filled from the selected postal record.
        self.assertEqual(job.pincode, "415001")
        self.assertEqual(job.district_name, "SATARA")
        self.assertEqual(job.state_name, "MAHARASHTRA")

        self.authenticate(self.admin)
        response = self.client.post("/jobs/admin/approve/", {"id": job.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.authenticate(self.applicant)
        response = self.client.post("/applications/apply/", {"job": job.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(JobApplication.objects.get().applicant, self.applicant)

    def test_user_cannot_apply_to_own_job(self):
        job = self.make_job(Job.Status.PUBLISHED)
        self.authenticate(self.poster)
        response = self.client.post("/applications/apply/", {"job": job.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("own job", str(response.data))

    def test_only_staff_can_approve_jobs(self):
        job = self.make_job(Job.Status.PENDING_APPROVAL)
        self.authenticate(self.poster)
        response = self.client.post("/jobs/admin/approve/", {"id": job.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)