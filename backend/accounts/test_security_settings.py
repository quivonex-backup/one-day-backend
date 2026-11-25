from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()

PASSWORD = "TestPassword123!"


class SecurityTestBase(APITestCase):

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="user@example.com", mobile_number="9400000001",
            password=PASSWORD, is_email_verified=True,
        )
        self.admin = User.objects.create_superuser(
            email="admin@example.com", mobile_number="9400000002", password=PASSWORD,
        )

    def tearDown(self):
        cache.clear()

    def login_as(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


class AuthRateLimitTests(SecurityTestBase):

    @mock.patch.object(ScopedRateThrottle, "THROTTLE_RATES", {"auth": "3/minute"})
    def test_login_is_rate_limited(self):
        body = {"email": "user@example.com", "password": "wrong-password"}

        for _ in range(3):
            response = self.client.post("/accounts/login/", body, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post("/accounts/login/", body, format="json")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @mock.patch.object(ScopedRateThrottle, "THROTTLE_RATES", {"auth": "2/minute"})
    def test_forgot_password_is_rate_limited(self):
        body = {"email": "user@example.com"}

        for _ in range(2):
            self.client.post("/accounts/forgot-password/", body, format="json")

        response = self.client.post("/accounts/forgot-password/", body, format="json")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @mock.patch.object(ScopedRateThrottle, "THROTTLE_RATES", {"auth": "2/minute"})
    def test_send_login_otp_is_rate_limited(self):
        for i in range(2):
            self.client.post(
                "/accounts/send-login-otp/",
                {"channel": "EMAIL", "identifier": f"person{i}@example.com"},
                format="json",
            )

        response = self.client.post(
            "/accounts/send-login-otp/",
            {"channel": "EMAIL", "identifier": "person9@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class TokenRefreshTests(SecurityTestBase):

    def test_refresh_gives_new_tokens_and_blocks_old_refresh_token(self):
        response = self.client.post(
            "/accounts/login/", {"email": "user@example.com", "password": PASSWORD}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        old_refresh = response.data["refresh"]

        response = self.client.post("/accounts/token/refresh/", {"refresh": old_refresh}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertNotEqual(response.data["refresh"], old_refresh)

        # Old refresh token cannot be used again (rotation + blacklist).
        response = self.client.post("/accounts/token/refresh/", {"refresh": old_refresh}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_new_access_token_works(self):
        refresh = RefreshToken.for_user(self.user)
        response = self.client.post("/accounts/token/refresh/", {"refresh": str(refresh)}, format="json")

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        response = self.client.post("/accounts/profile/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logged_out_refresh_token_cannot_be_used(self):
        refresh = RefreshToken.for_user(self.user)
        self.login_as(self.user)
        self.client.post("/accounts/logout/", {"refresh": str(refresh)}, format="json")

        self.client.credentials()
        response = self.client.post("/accounts/token/refresh/", {"refresh": str(refresh)}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ApiDocsAccessTests(SecurityTestBase):

    def test_anonymous_cannot_read_api_schema(self):
        response = self.client.get("/api/schema/")
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_normal_user_cannot_read_api_schema(self):
        self.login_as(self.user)
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_read_api_schema(self):
        self.login_as(self.admin)
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# Always test the server rules (DJANGO_DEBUG=False),
# even if .env has DJANGO_DEBUG=True on this machine.
@override_settings(
    CORS_ALLOW_ALL_ORIGINS=False,
    CORS_ALLOWED_ORIGINS=["http://localhost:5173"],
)
class CorsTests(SecurityTestBase):

    def test_unknown_website_is_not_allowed(self):
        response = self.client.options(
            "/jobs/find/",
            HTTP_ORIGIN="https://evil.example.com",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    def test_allowed_frontend_is_allowed(self):
        response = self.client.options(
            "/jobs/find/",
            HTTP_ORIGIN="http://localhost:5173",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "http://localhost:5173")
        
    def test_flutter_web_random_localhost_port_is_allowed(self):
        for origin in ("http://localhost:54871", "http://127.0.0.1:61234"):
            response = self.client.options(
                "/jobs/find/",
                HTTP_ORIGIN=origin,
                HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
                HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type",
            )
            self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), origin)

    def test_lookalike_localhost_domain_is_not_allowed(self):
        response = self.client.options(
            "/jobs/find/",
            HTTP_ORIGIN="http://localhost.evil.com",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)