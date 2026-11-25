from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from common.models import JobCategory, JobSubCategory, PostalLocation, Skill, State


User = get_user_model()


class CommonTestBase(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com", mobile_number="9200000001", password="TestPassword123!",
        )
        self.admin = User.objects.create_superuser(
            email="admin@example.com", mobile_number="9200000002", password="TestPassword123!",
        )

    def login(self, user):
        if user is None:
            self.client.credentials()
        else:
            token = RefreshToken.for_user(user).access_token
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def post(self, url, body=None, user=None):
        self.login(user)
        return self.client.post(url, body or {}, format="json")


class MasterDataPermissionTests(CommonTestBase):
    """Anyone can read master data. Only admin can create / update / delete."""

    def test_anonymous_cannot_create_skill(self):
        response = self.post("/common/skill/create/", {"name": "Welding"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(Skill.objects.exists())

    def test_normal_user_cannot_create_skill(self):
        response = self.post("/common/skill/create/", {"name": "Welding"}, self.user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Skill.objects.exists())

    def test_admin_can_create_skill(self):
        response = self.post("/common/skill/create/", {"name": "Welding"}, self.admin)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(Skill.objects.filter(name="Welding").exists())

    def test_normal_user_cannot_update_or_delete_skill(self):
        skill = Skill.objects.create(name="Welding")

        response = self.post("/common/skill/update/", {"id": skill.id, "name": "Changed"}, self.user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.post("/common/skill/delete/", {"id": skill.id}, self.user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        skill.refresh_from_db()
        self.assertEqual(skill.name, "Welding")

    def test_anyone_can_list_skills(self):
        Skill.objects.create(name="Welding")
        response = self.post("/common/skill/list/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([s["name"] for s in response.data["data"]], ["Welding"])

    def test_normal_user_cannot_create_job_category(self):
        response = self.post("/common/job-category/create/", {"name": "Farming"}, self.user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(JobCategory.objects.exists())

    def test_normal_user_cannot_create_state(self):
        response = self.post("/common/state/create/", {"name": "Goa", "state_code": "GA"}, self.user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(State.objects.exists())

    def test_admin_can_create_state(self):
        response = self.post("/common/state/create/", {"name": "Goa", "state_code": "GA"}, self.admin)
        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED), response.data)
        self.assertTrue(State.objects.filter(name="Goa").exists())


class JobSubCategoryTests(CommonTestBase):

    def setUp(self):
        super().setUp()
        self.construction = JobCategory.objects.create(name="Construction")
        self.logistics = JobCategory.objects.create(name="Logistics")

    def test_admin_can_create_subcategory(self):
        response = self.post(
            "/common/job-subcategory/create/",
            {"category": self.construction.id, "name": "Mason Helper"},
            self.admin,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["data"]["category_name"], "Construction")

    def test_normal_user_cannot_create_subcategory(self):
        response = self.post(
            "/common/job-subcategory/create/",
            {"category": self.construction.id, "name": "Mason Helper"},
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_name_in_same_category_is_blocked_ignoring_case(self):
        JobSubCategory.objects.create(category=self.construction, name="Painter")
        response = self.post(
            "/common/job-subcategory/create/",
            {"category": self.construction.id, "name": "painter"},
            self.admin,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_same_name_allowed_in_different_category(self):
        JobSubCategory.objects.create(category=self.construction, name="Helper")
        response = self.post(
            "/common/job-subcategory/create/",
            {"category": self.logistics.id, "name": "Helper"},
            self.admin,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_list_filters_by_category(self):
        mason = JobSubCategory.objects.create(category=self.construction, name="Mason Helper")
        JobSubCategory.objects.create(category=self.logistics, name="Loader")
        response = self.post("/common/job-subcategory/list/", {"category": self.construction.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([s["id"] for s in response.data["data"]], [mason.id])

    def test_delete_is_soft_and_hides_from_list(self):
        mason = JobSubCategory.objects.create(category=self.construction, name="Mason Helper")
        response = self.post("/common/job-subcategory/delete/", {"id": mason.id}, self.admin)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        mason.refresh_from_db()
        self.assertFalse(mason.is_active)

        response = self.post("/common/job-subcategory/list/")
        self.assertEqual(response.data["data"], [])


class PincodeLookupTests(CommonTestBase):

    def setUp(self):
        super().setUp()
        PostalLocation.objects.create(
            pincode="411005", post_office="Shivajinagar H.O",
            district_name="PUNE", state_name="MAHARASHTRA",
        )
        PostalLocation.objects.create(
            pincode="411005", post_office="Congress House Road S.O",
            district_name="PUNE", state_name="MAHARASHTRA",
        )

    def test_lookup_returns_all_post_offices_for_pincode(self):
        response = self.post("/common/location/lookup-by-pincode/", {"pincode": "411005"}, self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["requires_selection"])
        self.assertEqual(len(response.data["data"]), 2)

    def test_lookup_rejects_invalid_pincode(self):
        response = self.post("/common/location/lookup-by-pincode/", {"pincode": "41100"}, self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lookup_unknown_pincode_returns_404(self):
        response = self.post("/common/location/lookup-by-pincode/", {"pincode": "999999"}, self.user)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_lookup_requires_login(self):
        response = self.post("/common/location/lookup-by-pincode/", {"pincode": "411005"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        
class SuggestJobCategoryTests(CommonTestBase):

    def test_create_new_category(self):
        resp = self.post("/common/job-category/suggest/", {"name": "web development"}, self.user)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["is_new"])
        self.assertEqual(resp.data["data"]["name"], "Web Development")

    def test_duplicate_returns_existing(self):
        JobCategory.objects.create(name="Web Development")
        resp = self.post("/common/job-category/suggest/", {"name": "WEB DEVELOPMENT"}, self.user)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["is_new"])
        self.assertEqual(JobCategory.objects.filter(name__iexact="web development").count(), 1)

    def test_duplicate_mixed_case(self):
        JobCategory.objects.create(name="Data Entry")
        resp = self.post("/common/job-category/suggest/", {"name": "data entry"}, self.user)
        self.assertFalse(resp.data["is_new"])

    def test_empty_name_rejected(self):
        resp = self.post("/common/job-category/suggest/", {"name": ""}, self.user)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_short_name_rejected(self):
        resp = self.post("/common/job-category/suggest/", {"name": "A"}, self.user)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_rejected(self):
        resp = self.post("/common/job-category/suggest/", {"name": "Plumbing"})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class SuggestJobSubCategoryTests(CommonTestBase):

    def setUp(self):
        super().setUp()
        self.category = JobCategory.objects.create(name="Construction")

    def test_create_new_subcategory(self):
        resp = self.post(
            "/common/job-subcategory/suggest/",
            {"category_id": self.category.id, "name": "brick laying"},
            self.user,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["is_new"])
        self.assertEqual(resp.data["data"]["name"], "Brick Laying")

    def test_duplicate_returns_existing(self):
        JobSubCategory.objects.create(category=self.category, name="Brick Laying")
        resp = self.post(
            "/common/job-subcategory/suggest/",
            {"category_id": self.category.id, "name": "BRICK LAYING"},
            self.user,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["is_new"])

    def test_missing_category_id(self):
        resp = self.post("/common/job-subcategory/suggest/", {"name": "Painting"}, self.user)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_category_id(self):
        resp = self.post(
            "/common/job-subcategory/suggest/",
            {"category_id": 99999, "name": "Painting"},
            self.user,
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_empty_name_rejected(self):
        resp = self.post(
            "/common/job-subcategory/suggest/",
            {"category_id": self.category.id, "name": ""},
            self.user,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_rejected(self):
        resp = self.post(
            "/common/job-subcategory/suggest/",
            {"category_id": self.category.id, "name": "Welding"},
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)