from django.contrib.auth import get_user_model
from rest_framework import status

from subscriptions.models import BulkHiringRequest, SubscriptionPlan, UserSubscription
from .tests import SubscriptionTestBase


User = get_user_model()


class BulkHiringRequestTests(SubscriptionTestBase):
    """Bulk hiring request submission and admin review flow."""

    def request_body(self, **changes):
        data = {
            "title": "Need 50 workers for warehouse",
            "description": "We need 50 workers for our new warehouse in Pune for loading and unloading goods.",
            "number_of_workers": 50,
            "expected_duration_days": 7,
            "location": "Pune",
        }
        data.update(changes)
        return data

    # ---------- user endpoints ----------

    def test_user_can_submit_bulk_request(self):
        response = self.post("/subscriptions/bulk-hiring/request/", self.request_body(), self.user)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["data"]["status"], BulkHiringRequest.Status.PENDING)
        self.assertEqual(response.data["data"]["number_of_workers"], 50)

    def test_submit_needs_login(self):
        response = self.post("/subscriptions/bulk-hiring/request/", self.request_body())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_submit_validates_fields(self):
        bad_bodies = [
            self.request_body(title="Hi"),
            self.request_body(description="Too short"),
            self.request_body(number_of_workers=1),
            self.request_body(expected_duration_days=0),
        ]
        for body in bad_bodies:
            response = self.post("/subscriptions/bulk-hiring/request/", body, self.user)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, body)

    def test_max_3_pending_requests(self):
        for i in range(3):
            self.post(
                "/subscriptions/bulk-hiring/request/",
                self.request_body(title=f"Request {i} for workers"),
                self.user,
            )
        response = self.post(
            "/subscriptions/bulk-hiring/request/",
            self.request_body(title="Fourth request for workers"),
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("3 pending", response.data["message"])

    def test_my_requests_lists_own_only(self):
        self.post("/subscriptions/bulk-hiring/request/", self.request_body(), self.user)
        self.post(
            "/subscriptions/bulk-hiring/request/",
            self.request_body(title="Other user needs 20 helpers"),
            self.other,
        )

        response = self.post("/subscriptions/bulk-hiring/my-requests/", {}, self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_my_requests_filter_by_status(self):
        self.post("/subscriptions/bulk-hiring/request/", self.request_body(), self.user)
        response = self.post("/subscriptions/bulk-hiring/my-requests/", {"status": "APPROVED"}, self.user)
        self.assertEqual(response.data["count"], 0)

    # ---------- admin endpoints ----------

    def test_admin_lists_all_requests(self):
        self.post("/subscriptions/bulk-hiring/request/", self.request_body(), self.user)
        self.post(
            "/subscriptions/bulk-hiring/request/",
            self.request_body(title="Other user needs 20 helpers"),
            self.other,
        )

        response = self.post("/subscriptions/admin/bulk-hiring/", {}, self.admin)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_admin_views_detail(self):
        self.post("/subscriptions/bulk-hiring/request/", self.request_body(), self.user)
        req_id = BulkHiringRequest.objects.first().id

        response = self.post(
            "/subscriptions/admin/bulk-hiring/detail/",
            {"request_id": req_id},
            self.admin,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["user_email"], "user@example.com")

    def test_normal_user_cannot_access_admin_endpoints(self):
        for url in (
            "/subscriptions/admin/bulk-hiring/",
            "/subscriptions/admin/bulk-hiring/detail/",
            "/subscriptions/admin/bulk-hiring/approve/",
            "/subscriptions/admin/bulk-hiring/reject/",
        ):
            response = self.post(url, {"request_id": 999}, self.user)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, url)

    def test_admin_approves_request_creates_subscription(self):
        self.post("/subscriptions/bulk-hiring/request/", self.request_body(), self.user)
        req_id = BulkHiringRequest.objects.first().id

        custom_plan = self.make_plan(
            name="Warehouse 50", is_custom=True,
            job_post_limit=5, max_vacancies_per_job=50,
        )

        response = self.post(
            "/subscriptions/admin/bulk-hiring/approve/",
            {"request_id": req_id, "plan_id": custom_plan.id, "note": "Approved for Pune warehouse project"},
            self.admin,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        bulk_req = BulkHiringRequest.objects.get(id=req_id)
        self.assertEqual(bulk_req.status, BulkHiringRequest.Status.APPROVED)
        self.assertIsNotNone(bulk_req.subscription)
        self.assertEqual(bulk_req.subscription.status, UserSubscription.Status.ACTIVE)
        self.assertTrue(bulk_req.subscription.is_currently_active)
        self.assertEqual(bulk_req.subscription.max_vacancies_per_job, 50)
        self.assertEqual(bulk_req.reviewed_by, self.admin)

    def test_approve_needs_plan_and_note(self):
        self.post("/subscriptions/bulk-hiring/request/", self.request_body(), self.user)
        req_id = BulkHiringRequest.objects.first().id

        response = self.post(
            "/subscriptions/admin/bulk-hiring/approve/",
            {"request_id": req_id, "plan_id": self.basic_plan.id},
            self.admin,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_approve_already_reviewed(self):
        self.post("/subscriptions/bulk-hiring/request/", self.request_body(), self.user)
        req_id = BulkHiringRequest.objects.first().id
        custom_plan = self.make_plan(name="Custom bulk", is_custom=True, max_vacancies_per_job=50)

        self.post(
            "/subscriptions/admin/bulk-hiring/approve/",
            {"request_id": req_id, "plan_id": custom_plan.id, "note": "Approved first time"},
            self.admin,
        )
        response = self.post(
            "/subscriptions/admin/bulk-hiring/approve/",
            {"request_id": req_id, "plan_id": custom_plan.id, "note": "Trying again"},
            self.admin,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_rejects_request(self):
        self.post("/subscriptions/bulk-hiring/request/", self.request_body(), self.user)
        req_id = BulkHiringRequest.objects.first().id

        response = self.post(
            "/subscriptions/admin/bulk-hiring/reject/",
            {"request_id": req_id, "reason": "Location not supported yet"},
            self.admin,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        bulk_req = BulkHiringRequest.objects.get(id=req_id)
        self.assertEqual(bulk_req.status, BulkHiringRequest.Status.REJECTED)
        self.assertIn("Location", bulk_req.admin_note)

    def test_reject_needs_reason(self):
        self.post("/subscriptions/bulk-hiring/request/", self.request_body(), self.user)
        req_id = BulkHiringRequest.objects.first().id

        response = self.post(
            "/subscriptions/admin/bulk-hiring/reject/",
            {"request_id": req_id},
            self.admin,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_reject_already_reviewed(self):
        self.post("/subscriptions/bulk-hiring/request/", self.request_body(), self.user)
        req_id = BulkHiringRequest.objects.first().id

        self.post(
            "/subscriptions/admin/bulk-hiring/reject/",
            {"request_id": req_id, "reason": "Not needed anymore"},
            self.admin,
        )
        response = self.post(
            "/subscriptions/admin/bulk-hiring/reject/",
            {"request_id": req_id, "reason": "Trying again"},
            self.admin,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)