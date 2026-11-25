from rest_framework import status

from applications.models import JobApplication
from jobs.models import Job
from jobs.tests import JobTestBase


class AdminApprovalTests(JobTestBase):
    """Admin can approve or reject only jobs waiting for approval."""

    def approve(self, job, user=None):
        self.login(user or self.admin)
        return self.client.post("/jobs/admin/approve/", {"id": job.id}, format="json")

    def reject(self, job, reason="Job description is not clear.", user=None):
        self.login(user or self.admin)
        return self.client.post("/jobs/admin/reject/", {"id": job.id, "reason": reason}, format="json")

    def test_admin_approves_pending_job(self):
        job = self.make_job(status_value=Job.Status.PENDING_APPROVAL)
        response = self.approve(job)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.PUBLISHED)
        self.assertEqual(job.approved_by, self.admin)
        self.assertIsNotNone(job.approved_at)

    def test_cannot_approve_job_that_is_not_pending(self):
        for status_value in (Job.Status.CANCELLED, Job.Status.CLOSED, Job.Status.REJECTED, Job.Status.PUBLISHED):
            job = self.make_job(status_value=status_value, title=f"Job {status_value}")
            response = self.approve(job)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, status_value)
            job.refresh_from_db()
            self.assertEqual(job.status, status_value)

    def test_cannot_approve_job_after_deadline(self):
        job = self.make_job(status_value=Job.Status.PENDING_APPROVAL, deadline_days=-1)
        response = self.approve(job)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("deadline", response.data["message"])

    def test_normal_user_cannot_approve_or_reject(self):
        job = self.make_job(status_value=Job.Status.PENDING_APPROVAL)

        self.assertEqual(self.approve(job, user=self.other).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.reject(job, user=self.owner).status_code, status.HTTP_403_FORBIDDEN)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.PENDING_APPROVAL)

    def test_reject_saves_reason_and_admin(self):
        job = self.make_job(status_value=Job.Status.PENDING_APPROVAL)
        response = self.reject(job, reason="Wage is below minimum wage.")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.REJECTED)
        self.assertEqual(job.rejected_by, self.admin)
        self.assertEqual(job.rejection_reason, "Wage is below minimum wage.")

    def test_reject_requires_reason(self):
        job = self.make_job(status_value=Job.Status.PENDING_APPROVAL)
        response = self.reject(job, reason="  ")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.PENDING_APPROVAL)

    def test_cannot_reject_published_job(self):
        job = self.make_job(status_value=Job.Status.PUBLISHED)
        response = self.reject(job)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_owner_sees_rejection_reason(self):
        job = self.make_job(status_value=Job.Status.PENDING_APPROVAL)
        self.reject(job, reason="Please add the exact work address.")

        self.login(self.owner)
        response = self.client.post("/jobs/detail/", {"id": job.id}, format="json")
        self.assertEqual(response.data["data"]["rejection_reason"], "Please add the exact work address.")


class OwnerStatusTests(JobTestBase):
    """Owner edit / close / cancel rules."""

    def post_as_owner(self, url, body):
        self.login(self.owner)
        return self.client.post(url, body, format="json")

    def test_editing_rejected_job_sends_it_back_for_approval(self):
        job = self.make_job(status_value=Job.Status.REJECTED)
        job.rejection_reason = "Unclear description."
        job.rejected_by = self.admin
        job.save()

        response = self.post_as_owner("/jobs/update/", {"id": job.id, "job_title": "Mason Helper - Updated"})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.PENDING_APPROVAL)
        self.assertEqual(job.rejection_reason, "")
        self.assertIsNone(job.rejected_by)

    def test_editing_published_job_needs_approval_again(self):
        job = self.make_job(status_value=Job.Status.PUBLISHED, approved_by=self.admin)
        response = self.post_as_owner("/jobs/update/", {"id": job.id, "daily_wage": "800.00"})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.PENDING_APPROVAL)
        self.assertIsNone(job.approved_by)

    def test_cannot_edit_closed_cancelled_or_completed_job(self):
        for status_value in (Job.Status.CLOSED, Job.Status.CANCELLED, Job.Status.COMPLETED):
            job = self.make_job(status_value=status_value, title=f"Job {status_value}")
            response = self.post_as_owner("/jobs/update/", {"id": job.id, "job_title": "Changed title"})

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, status_value)
            job.refresh_from_db()
            self.assertEqual(job.status, status_value)

    def test_close_only_published_job(self):
        published = self.make_job(status_value=Job.Status.PUBLISHED)
        pending = self.make_job(status_value=Job.Status.PENDING_APPROVAL, title="Pending job")

        self.assertEqual(self.post_as_owner("/jobs/close/", {"id": published.id}).status_code, status.HTTP_200_OK)
        self.assertEqual(self.post_as_owner("/jobs/close/", {"id": pending.id}).status_code, status.HTTP_400_BAD_REQUEST)

        published.refresh_from_db()
        pending.refresh_from_db()
        self.assertEqual(published.status, Job.Status.CLOSED)
        self.assertEqual(pending.status, Job.Status.PENDING_APPROVAL)

    def test_cancel_cancels_waiting_applications(self):
        job = self.make_job(status_value=Job.Status.PUBLISHED)
        applied = JobApplication.objects.create(job=job, applicant=self.other)

        response = self.post_as_owner("/jobs/cancel/", {"id": job.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        job.refresh_from_db()
        applied.refresh_from_db()
        self.assertEqual(job.status, Job.Status.CANCELLED)
        self.assertEqual(applied.status, JobApplication.Status.CANCELLED)

    def test_cannot_cancel_job_with_hired_worker(self):
        job = self.make_job(status_value=Job.Status.PUBLISHED)
        JobApplication.objects.create(job=job, applicant=self.other, status=JobApplication.Status.HIRED)

        response = self.post_as_owner("/jobs/cancel/", {"id": job.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.PUBLISHED)

    def test_cannot_cancel_closed_job(self):
        job = self.make_job(status_value=Job.Status.CLOSED)
        response = self.post_as_owner("/jobs/cancel/", {"id": job.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AdminFlagTests(JobTestBase):

    def toggle(self, url, job):
        self.login(self.admin)
        return self.client.post(url, {"id": job.id}, format="json")

    def test_feature_and_urgent_toggle_on_published_job(self):
        job = self.make_job(status_value=Job.Status.PUBLISHED)

        response = self.toggle("/jobs/admin/feature/", job)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_featured"])

        response = self.toggle("/jobs/admin/urgent/", job)
        self.assertTrue(response.data["is_urgent"])

        response = self.toggle("/jobs/admin/feature/", job)
        self.assertFalse(response.data["is_featured"])

    def test_cannot_feature_unpublished_job(self):
        job = self.make_job(status_value=Job.Status.PENDING_APPROVAL)
        response = self.toggle("/jobs/admin/feature/", job)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        job.refresh_from_db()
        self.assertFalse(job.is_featured)