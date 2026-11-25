from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from subscriptions.models import SubscriptionPlan, UserSubscription
from applications.models import JobApplication
from common.models import JobCategory, JobSubCategory, PostalLocation
from jobs.models import Job


User = get_user_model()


class JobTestBase(APITestCase):
    """Shared users, master data and helpers for job tests."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com", mobile_number="9100000001", password="TestPassword123!",
        )
        self.other = User.objects.create_user(
            email="other@example.com", mobile_number="9100000002", password="TestPassword123!",
        )
        self.admin = User.objects.create_superuser(
            email="admin@example.com", mobile_number="9100000003", password="TestPassword123!",
        )

        self.satara = PostalLocation.objects.create(
            pincode="415001", post_office="Satara H.O",
            district_name="SATARA", state_name="MAHARASHTRA",
        )
        self.pune = PostalLocation.objects.create(
            pincode="411005", post_office="Shivajinagar H.O",
            district_name="PUNE", state_name="MAHARASHTRA",
        )

        self.construction = JobCategory.objects.create(name="Construction")
        self.mason = JobSubCategory.objects.create(category=self.construction, name="Mason Helper")
        self.logistics = JobCategory.objects.create(name="Logistics")
        self.loader = JobSubCategory.objects.create(category=self.logistics, name="Loader")
        plan = SubscriptionPlan.objects.create(
            name="Test Plan", price="0.00", validity_days=365,
            job_post_limit=100, max_vacancies_per_job=100,
        )
        for user in (self.owner, self.other):
            sub = UserSubscription.from_plan(user, plan, UserSubscription.Source.FREE)
            sub.activate()
            sub.save()
    # ---------- helpers ----------

    def login(self, user):
        if user is None:
            self.client.credentials()
        else:
            token = RefreshToken.for_user(user).access_token
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def payload(self, **changes):
        today = timezone.localdate()
        data = {
            "job_title": "Mason Helper Needed",
            "job_category": self.construction.pk,
            "job_subcategory": self.mason.pk,
            "job_duration": "ONE_DAY",
            "job_description": "Need one helper for house construction work for one day.",
            "salary_type": "DAILY",
            "daily_wage": "700.00",
            "address": "Near Gram Panchayat Office, Main Road",
            "postal_location_id": self.satara.pk,
            "start_time": "08:00",
            "end_time": "17:00",
            "job_start_date": str(today + timedelta(days=5)),
            "job_end_date": str(today + timedelta(days=5)),
            "application_deadline": str(today + timedelta(days=3)),
        }
        data.update(changes)
        return data

    def make_job(self, owner=None, location=None, status_value=Job.Status.PUBLISHED,
                 title="Mason Helper Needed", deadline_days=3, **extra):
        today = timezone.localdate()
        return Job.objects.create(
            posted_by=owner or self.owner,
            status=status_value,
            job_title=title,
            job_category=self.construction,
            job_subcategory=self.mason,
            job_duration="ONE_DAY",
            job_description="Need one helper for house construction work for one day.",
            salary_type="DAILY",
            daily_wage=700,
            address="Near Gram Panchayat Office, Main Road",
            postal_location=location or self.satara,
            start_time="08:00",
            end_time="17:00",
            job_start_date=today + timedelta(days=5),
            job_end_date=today + timedelta(days=5),
            application_deadline=today + timedelta(days=deadline_days),
            **extra,
        )


class JobLocationTests(JobTestBase):
    """Job create/update stores location from PostalLocation."""

    def test_create_job_fills_location_from_postal_location(self):
        self.login(self.owner)
        response = self.client.post("/jobs/create/", self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        data = response.data["data"]
        self.assertEqual(data["pincode"], "415001")
        self.assertEqual(data["district_name"], "SATARA")
        self.assertEqual(data["state_name"], "MAHARASHTRA")
        self.assertEqual(data["postal_location"]["post_office"], "Satara H.O")
        self.assertEqual(data["status"], Job.Status.PENDING_APPROVAL)

    def test_create_job_ignores_location_text_sent_by_frontend(self):
        self.login(self.owner)
        response = self.client.post(
            "/jobs/create/",
            self.payload(pincode="999999", district_name="FAKE", state_name="FAKE"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        job = Job.objects.get(pk=response.data["data"]["id"])
        self.assertEqual(job.pincode, "415001")
        self.assertEqual(job.district_name, "SATARA")

    def test_create_job_requires_postal_location(self):
        self.login(self.owner)
        data = self.payload()
        data.pop("postal_location_id")
        response = self.client.post("/jobs/create/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("postal_location_id", response.data)

    def test_create_job_rejects_unknown_postal_location(self):
        self.login(self.owner)
        response = self.client.post("/jobs/create/", self.payload(postal_location_id=999999), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("postal_location_id", response.data)

    def test_create_job_rejects_subcategory_from_other_category(self):
        self.login(self.owner)
        response = self.client.post(
            "/jobs/create/",
            self.payload(job_category=self.construction.pk, job_subcategory=self.loader.pk),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("job_subcategory", response.data)

    def test_update_job_location_refills_pincode_district_state(self):
        job = self.make_job()
        self.login(self.owner)
        response = self.client.post(
            "/jobs/update/",
            {"id": job.id, "postal_location_id": self.pune.pk, "pincode": "999999"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        job.refresh_from_db()
        self.assertEqual(job.pincode, "411005")
        self.assertEqual(job.district_name, "PUNE")
        self.assertEqual(job.status, Job.Status.PENDING_APPROVAL)

    def test_create_job_requires_login(self):
        self.login(None)
        response = self.client.post("/jobs/create/", self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class JobOwnershipTests(JobTestBase):
    """Only the job owner can see, edit, close or delete their job."""

    def test_other_user_cannot_view_owner_job_detail(self):
        job = self.make_job()
        self.login(self.other)
        response = self.client.post("/jobs/detail/", {"id": job.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_other_user_cannot_update_job(self):
        job = self.make_job()
        self.login(self.other)
        response = self.client.post("/jobs/update/", {"id": job.id, "job_title": "Hacked title"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        job.refresh_from_db()
        self.assertEqual(job.job_title, "Mason Helper Needed")

    def test_other_user_cannot_delete_job(self):
        job = self.make_job()
        self.login(self.other)
        response = self.client.post("/jobs/delete/", {"id": job.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        job.refresh_from_db()
        self.assertTrue(job.is_active)

    def test_other_user_cannot_close_job(self):
        job = self.make_job()
        self.login(self.other)
        response = self.client.post("/jobs/close/", {"id": job.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.PUBLISHED)

    def test_owner_can_soft_delete_job(self):
        job = self.make_job()
        self.login(self.owner)
        response = self.client.post("/jobs/delete/", {"id": job.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        job.refresh_from_db()
        self.assertFalse(job.is_active)

    def test_hard_delete_blocked_when_job_has_applications(self):
        job = self.make_job()
        JobApplication.objects.create(job=job, applicant=self.other)
        self.login(self.owner)
        response = self.client.post("/jobs/hard-delete/", {"id": job.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Job.objects.filter(pk=job.pk).exists())

    def test_hard_delete_allowed_without_applications(self):
        job = self.make_job()
        self.login(self.owner)
        response = self.client.post("/jobs/hard-delete/", {"id": job.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Job.objects.filter(pk=job.pk).exists())

    def test_my_jobs_lists_only_own_jobs(self):
        mine = self.make_job()
        self.make_job(owner=self.other, title="Other user job")
        self.login(self.owner)
        response = self.client.post("/jobs/my-jobs/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([j["id"] for j in response.data["data"]], [mine.id])


class FindJobsTests(JobTestBase):
    """Public Find Jobs search with location filters."""

    def setUp(self):
        super().setUp()
        self.satara_job = self.make_job(location=self.satara, title="Mason Helper Satara")
        self.pune_job = self.make_job(location=self.pune, title="Loader Pune")

    def find(self, body, user=None):
        self.login(user)
        response = self.client.post("/jobs/find/", body, format="json")
        ids = [j["id"] for j in response.data.get("data", [])]
        return response, ids

    def test_no_filters_returns_published_jobs(self):
        response, ids = self.find({})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(ids, [self.satara_job.id, self.pune_job.id])

    def test_filter_by_pincode(self):
        _, ids = self.find({"pincode": "411005"})
        self.assertEqual(ids, [self.pune_job.id])

    def test_filter_by_district_ignores_case(self):
        _, ids = self.find({"district": "satara"})
        self.assertEqual(ids, [self.satara_job.id])

    def test_filter_by_state(self):
        _, ids = self.find({"state": "maharashtra"})
        self.assertEqual(len(ids), 2)
        _, ids = self.find({"state": "goa"})
        self.assertEqual(ids, [])

    def test_keyword_and_location_together(self):
        _, ids = self.find({"keyword": "loader", "district": "pune"})
        self.assertEqual(ids, [self.pune_job.id])
        _, ids = self.find({"keyword": "loader", "district": "satara"})
        self.assertEqual(ids, [])

    def test_invalid_pincode_returns_400(self):
        response, _ = self.find({"pincode": "41500"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unpublished_and_inactive_jobs_are_hidden(self):
        pending = self.make_job(status_value=Job.Status.PENDING_APPROVAL, title="Pending job")
        inactive = self.make_job(title="Inactive job", is_active=False)
        _, ids = self.find({})
        self.assertNotIn(pending.id, ids)
        self.assertNotIn(inactive.id, ids)

    def test_expired_deadline_jobs_are_hidden(self):
        expired = self.make_job(title="Expired job", deadline_days=-1)
        _, ids = self.find({})
        self.assertNotIn(expired.id, ids)

    def test_logged_in_user_does_not_see_own_jobs(self):
        _, ids = self.find({}, user=self.owner)
        self.assertEqual(ids, [])
        other_job = self.make_job(owner=self.other, title="Other user job")
        _, ids = self.find({}, user=self.owner)
        self.assertEqual(ids, [other_job.id])

    def test_use_profile_location_needs_login(self):
        response, _ = self.find({"use_profile_location": True})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_pagination(self):
        response, ids = self.find({"page": 1, "page_size": 1})
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["total_pages"], 2)
        self.assertEqual(len(ids), 1)


class CloseExpiredJobsCommandTests(JobTestBase):

    def call_command(self, *args):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command("close_expired_jobs", *args, stdout=out)
        return out.getvalue()

    def test_closes_expired_published_jobs(self):
        job = self.make_job(deadline_days=-1)
        output = self.call_command()
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.CLOSED)
        self.assertIn("1 job(s) closed", output)

    def test_skips_non_published_jobs(self):
        job = self.make_job(deadline_days=-1, status_value=Job.Status.PENDING_APPROVAL)
        self.call_command()
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.PENDING_APPROVAL)

    def test_skips_future_deadline(self):
        job = self.make_job(deadline_days=5)
        self.call_command()
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.PUBLISHED)

    def test_dry_run_does_not_change(self):
        job = self.make_job(deadline_days=-1)
        output = self.call_command("--dry-run")
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.PUBLISHED)
        self.assertIn("DRY RUN", output)

    def test_cancels_applied_applications(self):
        job = self.make_job(deadline_days=-1)
        app = JobApplication.objects.create(job=job, applicant=self.other, status=JobApplication.Status.APPLIED)
        self.call_command()
        app.refresh_from_db()
        self.assertEqual(app.status, JobApplication.Status.CANCELLED)

    def test_does_not_cancel_hired_applications(self):
        job = self.make_job(deadline_days=-1)
        app = JobApplication.objects.create(job=job, applicant=self.other, status=JobApplication.Status.HIRED)
        self.call_command()
        app.refresh_from_db()
        self.assertEqual(app.status, JobApplication.Status.HIRED)
        
        
class AppliedCountTests(JobTestBase):

    def test_published_jobs_include_applied_count(self):
        job = self.make_job()
        JobApplication.objects.create(job=job, applicant=self.other, status=JobApplication.Status.APPLIED)
        self.login(self.owner)
        resp = self.client.post("/jobs/published/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["data"][0]["applied_count"], 1)

    def test_admin_published_includes_applied_count(self):
        job = self.make_job()
        JobApplication.objects.create(job=job, applicant=self.other, status=JobApplication.Status.APPLIED)
        JobApplication.objects.create(job=job, applicant=self.owner, status=JobApplication.Status.APPLIED)
        self.login(self.admin)
        resp = self.client.post("/jobs/admin/published/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["data"][0]["applied_count"], 2)

    def test_inactive_applications_not_counted(self):
        job = self.make_job()
        JobApplication.objects.create(job=job, applicant=self.other, status=JobApplication.Status.APPLIED, is_active=False)
        self.login(self.owner)
        resp = self.client.post("/jobs/published/")
        self.assertEqual(resp.data["data"][0]["applied_count"], 0)
        
