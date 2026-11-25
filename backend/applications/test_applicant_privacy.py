from datetime import date

from rest_framework import status

from accounts.models import UserProfile
from applications.models import JobApplication
from common.models import Skill
from jobs.tests import JobTestBase


# Fields that must NEVER reach the other person.
PRIVATE_PROFILE_FIELDS = ("address", "pincode", "date_of_birth", "postal_location", "user")


class ApplicantPrivacyTests(JobTestBase):

    def setUp(self):
        super().setUp()
        self.job = self.make_job()  # owned by self.owner

        # Applicant (self.other) with a full profile.
        self.welding = Skill.objects.create(name="Welding")
        self.profile = UserProfile.objects.create(
            user=self.other,
            full_name="Ravi Patil",
            gender="MALE",
            date_of_birth=date(1995, 1, 1),
            address="House 12, Secret Lane",
            pincode="415001",
            city="SATARA",
            state="MAHARASHTRA",
            experience_years=3,
            expected_wage="700.00",
            expected_wage_type="DAILY",
            about="Hard working mason helper.",
        )
        self.profile.skills.set([self.welding])

        UserProfile.objects.create(user=self.owner, full_name="Suresh Shinde", business_name="Shinde Builders")

        self.application = JobApplication.objects.create(job=self.job, applicant=self.other)

    # ---------- helpers ----------

    def owner_list(self):
        self.login(self.owner)
        response = self.client.post("/applications/applicants/", {"job_id": self.job.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data["data"][0]

    def owner_detail(self):
        self.login(self.owner)
        response = self.client.post(
            "/applications/applicant-details/", {"application_id": self.application.id}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data["data"]

    def applicant_detail(self):
        self.login(self.other)
        response = self.client.post(
            "/applications/details/", {"application_id": self.application.id}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data["data"]

    def set_status(self, value):
        self.application.status = value
        self.application.save()

    # ---------- job owner view ----------

    def test_owner_sees_work_profile(self):
        data = self.owner_list()
        profile = data["applicant_profile"]

        self.assertEqual(profile["full_name"], "Ravi Patil")
        self.assertEqual(profile["skills"], ["Welding"])
        self.assertEqual(profile["experience_years"], 3)
        self.assertEqual(profile["district"], "SATARA")
        self.assertEqual(profile["state"], "MAHARASHTRA")
        self.assertIsInstance(profile["age"], int)
        self.assertEqual(data["job_title"], self.job.job_title)

    def test_owner_never_sees_address_pincode_or_birth_date(self):
        for data in (self.owner_list(), self.owner_detail()):
            profile = data["applicant_profile"]
            for field in PRIVATE_PROFILE_FIELDS:
                self.assertNotIn(field, profile)
            self.assertNotIn("Secret Lane", str(data))

    def test_owner_does_not_see_contact_before_hiring(self):
        for value in (JobApplication.Status.APPLIED, JobApplication.Status.SHORTLISTED, JobApplication.Status.REJECTED):
            self.set_status(value)
            for data in (self.owner_list(), self.owner_detail()):
                self.assertIsNone(data["applicant_contact"], value)
                self.assertNotIn(self.other.mobile_number, str(data))
                self.assertNotIn(self.other.email, str(data))

    def test_owner_sees_contact_after_hiring(self):
        for value in (JobApplication.Status.HIRED, JobApplication.Status.COMPLETED):
            self.set_status(value)
            data = self.owner_detail()
            self.assertEqual(data["applicant_contact"]["mobile_number"], self.other.mobile_number)
            self.assertEqual(data["applicant_contact"]["email"], self.other.email)

    def test_owner_sees_contact_after_hire_api(self):
        self.login(self.owner)
        self.client.post(f"/applications/shortlist/{self.application.id}/", {}, format="json")
        self.assertIsNone(self.owner_detail()["applicant_contact"])

        self.login(self.owner)
        self.client.post(f"/applications/hire/{self.application.id}/", {}, format="json")
        self.assertIsNotNone(self.owner_detail()["applicant_contact"])

    def test_applicant_without_profile_does_not_crash(self):
        third = self.admin.__class__.objects.create_user(
            email="third@example.com", mobile_number="9100000009", password="TestPassword123!",
        )
        JobApplication.objects.create(job=self.job, applicant=third)

        self.login(self.owner)
        response = self.client.post("/applications/applicants/", {"job_id": self.job.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        profiles = [a["applicant_profile"] for a in response.data["data"]]
        self.assertIn(None, profiles)

    def test_other_user_cannot_see_applicant_profile(self):
        third = self.admin.__class__.objects.create_user(
            email="third@example.com", mobile_number="9100000009", password="TestPassword123!",
        )
        self.login(third)
        response = self.client.post(
            "/applications/applicant-details/", {"application_id": self.application.id}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertNotIn("Ravi", str(response.data))

    # ---------- applicant view ----------

    def test_applicant_sees_job_summary_and_poster_name(self):
        data = self.applicant_detail()
        self.assertEqual(data["job_title"], self.job.job_title)
        self.assertEqual(data["job_district"], "SATARA")
        self.assertEqual(data["poster_name"], "Shinde Builders")

    def test_applicant_does_not_see_poster_contact_before_hiring(self):
        data = self.applicant_detail()
        self.assertIsNone(data["poster_contact"])
        self.assertNotIn(self.owner.mobile_number, str(data))
        self.assertNotIn(self.owner.email, str(data))

    def test_applicant_sees_poster_contact_after_hiring(self):
        self.set_status(JobApplication.Status.HIRED)
        data = self.applicant_detail()
        self.assertEqual(data["poster_contact"]["mobile_number"], self.owner.mobile_number)

    def test_my_applications_list_hides_contact_until_hired(self):
        self.login(self.other)
        response = self.client.post("/applications/my-applications/", {}, format="json")
        self.assertIsNone(response.data["data"][0]["poster_contact"])

        self.set_status(JobApplication.Status.HIRED)
        response = self.client.post("/applications/my-applications/", {}, format="json")
        self.assertIsNotNone(response.data["data"][0]["poster_contact"])