from django.contrib.auth import get_user_model
from rest_framework import status

from applications.models import JobApplication
from jobs.models import Job
from jobs.tests import JobTestBase


User = get_user_model()


class ApplyJobTests(JobTestBase):
    """Rules for applying to a job."""

    def setUp(self):
        super().setUp()
        self.job = self.make_job()  # published job owned by self.owner

    def apply(self, user, job_id=None):
        self.login(user)
        return self.client.post("/applications/apply/", {"job": job_id or self.job.id}, format="json")

    def test_user_can_apply_to_other_users_job(self):
        response = self.apply(self.other)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        application = JobApplication.objects.get()
        self.assertEqual(application.applicant, self.other)
        self.assertEqual(application.status, JobApplication.Status.APPLIED)

    def test_cannot_apply_twice_to_same_job(self):
        self.apply(self.other)
        response = self.apply(self.other)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already applied", str(response.data))
        self.assertEqual(JobApplication.objects.count(), 1)

    def test_duplicate_blocked_by_database_rule_returns_400_not_500(self):
        # An inactive old application passes the serializer check,
        # so the database unique rule must catch it.
        JobApplication.objects.create(job=self.job, applicant=self.other, is_active=False)
        response = self.apply(self.other)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already applied", str(response.data))

    def test_cannot_apply_to_own_job(self):
        response = self.apply(self.owner)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("own job", str(response.data))
        self.assertFalse(JobApplication.objects.exists())

    def test_cannot_apply_to_unpublished_job(self):
        pending = self.make_job(status_value=Job.Status.PENDING_APPROVAL, title="Pending job")
        response = self.apply(self.other, pending.id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("published", str(response.data))

    def test_cannot_apply_to_inactive_job(self):
        inactive = self.make_job(title="Inactive job", is_active=False)
        response = self.apply(self.other, inactive.id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_apply_after_deadline(self):
        expired = self.make_job(title="Expired job", deadline_days=-1)
        response = self.apply(self.other, expired.id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("deadline", str(response.data))

    def test_apply_requires_login(self):
        response = self.apply(None)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MyApplicationsTests(JobTestBase):
    """Applicant can see and cancel only their own applications."""

    def setUp(self):
        super().setUp()
        self.third = User.objects.create_user(
            email="third@example.com", mobile_number="9100000004", password="TestPassword123!",
        )
        self.job = self.make_job()
        self.application = JobApplication.objects.create(job=self.job, applicant=self.other)

    def test_my_applications_lists_only_own(self):
        JobApplication.objects.create(job=self.job, applicant=self.third)
        self.login(self.other)
        response = self.client.post("/applications/my-applications/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([a["id"] for a in response.data["data"]], [self.application.id])

    def test_other_user_cannot_view_application_detail(self):
        self.login(self.third)
        response = self.client.post(
            "/applications/details/", {"application_id": self.application.id}, format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_applicant_can_cancel_own_application(self):
        self.login(self.other)
        response = self.client.post(f"/applications/cancel/{self.application.id}/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, JobApplication.Status.CANCELLED)

    def test_other_user_cannot_cancel_application(self):
        self.login(self.third)
        response = self.client.post(f"/applications/cancel/{self.application.id}/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, JobApplication.Status.APPLIED)


class ManageApplicantsTests(JobTestBase):
    """Only the job owner can view and manage applicants."""

    def setUp(self):
        super().setUp()
        self.job = self.make_job()
        self.application = JobApplication.objects.create(job=self.job, applicant=self.other)

    def test_owner_can_list_applicants(self):
        self.login(self.owner)
        response = self.client.post("/applications/applicants/", {"job_id": self.job.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([a["id"] for a in response.data["data"]], [self.application.id])

    def test_non_owner_cannot_list_applicants(self):
        self.login(self.other)
        response = self.client.post("/applications/applicants/", {"job_id": self.job.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_owner_cannot_view_applicant_detail(self):
        self.login(self.other)
        response = self.client.post(
            "/applications/applicant-details/", {"application_id": self.application.id}, format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_owner_cannot_shortlist(self):
        self.login(self.other)
        response = self.client.post(f"/applications/shortlist/{self.application.id}/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, JobApplication.Status.APPLIED)

    def test_owner_status_flow_applied_shortlisted_hired_completed(self):
        self.login(self.owner)
        for action, expected in (
            ("shortlist", JobApplication.Status.SHORTLISTED),
            ("hire", JobApplication.Status.HIRED),
            ("complete", JobApplication.Status.COMPLETED),
        ):
            response = self.client.post(f"/applications/{action}/{self.application.id}/", {}, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.application.refresh_from_db()
            self.assertEqual(self.application.status, expected)

    def test_owner_cannot_hire_without_shortlisting(self):
        self.login(self.owner)
        response = self.client.post(f"/applications/hire/{self.application.id}/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, JobApplication.Status.APPLIED)

    def test_owner_can_reject_applicant(self):
        self.login(self.owner)
        response = self.client.post(f"/applications/reject/{self.application.id}/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, JobApplication.Status.REJECTED)