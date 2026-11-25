import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import OTPVerification
from accounts.utils import MAX_OTP_ATTEMPTS


User = get_user_model()

PASSWORD = "OldPassword123!"
NEW_PASSWORD = "NewPassword456!"


def otp_from_last_email():
    """Read the 6-digit OTP from the last email sent."""
    return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)


def wrong_otp(correct):
    return "000000" if correct != "000000" else "111111"


class OTPTestBase(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            mobile_number="9300000001",
            password=PASSWORD,
            is_email_verified=True,
        )

    def post(self, url, body):
        return self.client.post(url, body, format="json")

    def make_otp_old(self, user, otp_type):
        # Move the OTP's creation time back so the 60-second cooldown has passed.
        OTPVerification.objects.filter(user=user, otp_type=otp_type).update(
            created_at=timezone.now() - timedelta(minutes=2)
        )


class EmailVerificationOTPTests(OTPTestBase):

    def register(self):
        return self.post("/accounts/register/", {
            "full_name": "New User",
            "email": "New@Example.com",
            "mobile_number": "9300000002",
            "password": PASSWORD,
            "confirm_password": PASSWORD,
        })

    def test_otp_is_stored_hashed_not_plain(self):
        self.register()
        otp = otp_from_last_email()
        record = OTPVerification.objects.get(user__email="new@example.com")

        self.assertNotEqual(record.otp, otp)
        self.assertNotIn(otp, record.otp)

    def test_correct_otp_verifies_email_once(self):
        self.register()
        otp = otp_from_last_email()

        response = self.post("/accounts/verify-email/", {"email": "new@example.com", "otp": otp})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(User.objects.get(email="new@example.com").is_email_verified)

        # Same OTP cannot be used again.
        response = self.post("/accounts/verify-email/", {"email": "new@example.com", "otp": otp})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_otp_blocked_after_too_many_wrong_attempts(self):
        self.register()
        otp = otp_from_last_email()

        for _ in range(MAX_OTP_ATTEMPTS):
            response = self.post("/accounts/verify-email/", {"email": "new@example.com", "otp": wrong_otp(otp)})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Even the correct OTP no longer works.
        response = self.post("/accounts/verify-email/", {"email": "new@example.com", "otp": otp})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Too many", response.data["message"])
        self.assertFalse(User.objects.get(email="new@example.com").is_email_verified)

    def test_expired_otp_is_rejected(self):
        self.register()
        otp = otp_from_last_email()
        OTPVerification.objects.update(expires_at=timezone.now() - timedelta(seconds=1))

        response = self.post("/accounts/verify-email/", {"email": "new@example.com", "otp": otp})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_unknown_email_returns_400_not_404(self):
        response = self.post("/accounts/verify-email/", {"email": "nobody@example.com", "otp": "123456"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resend_has_cooldown(self):
        self.register()
        sent_before = len(mail.outbox)

        response = self.post("/accounts/resend-otp/", {"email": "new@example.com"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), sent_before)  # blocked by cooldown

        self.make_otp_old(User.objects.get(email="new@example.com"), OTPVerification.OTPType.EMAIL_VERIFICATION)
        self.post("/accounts/resend-otp/", {"email": "new@example.com"})
        self.assertEqual(len(mail.outbox), sent_before + 1)

    def test_resend_gives_same_answer_for_unknown_email(self):
        known = self.post("/accounts/resend-otp/", {"email": "user@example.com"})
        unknown = self.post("/accounts/resend-otp/", {"email": "nobody@example.com"})

        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.data, unknown.data)


class PasswordResetOTPTests(OTPTestBase):

    def forgot(self, email="user@example.com"):
        return self.post("/accounts/forgot-password/", {"email": email})

    def reset(self, otp, email="user@example.com"):
        return self.post("/accounts/reset-password/", {
            "email": email,
            "otp": otp,
            "password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        })

    def test_forgot_password_same_answer_for_unknown_email(self):
        known = self.forgot()
        unknown = self.forgot("nobody@example.com")

        self.assertEqual(known.status_code, status.HTTP_200_OK)
        self.assertEqual(known.data, unknown.data)
        self.assertEqual(len(mail.outbox), 1)  # email sent only to the real account

    def test_full_reset_flow_and_logout_everywhere(self):
        old_refresh = RefreshToken.for_user(self.user)

        self.forgot()
        otp = otp_from_last_email()

        response = self.post("/accounts/verify-reset-otp/", {"email": "user@example.com", "otp": otp})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        response = self.reset(otp)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

        # Old refresh token is blacklisted.
        self.assertTrue(BlacklistedToken.objects.filter(token__jti=old_refresh["jti"]).exists())

        # OTP cannot be reused.
        response = self.reset(otp)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Login works with the new password.
        response = self.post("/accounts/login/", {"email": "user@example.com", "password": NEW_PASSWORD})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_reset_works_without_verify_step(self):
        self.forgot()
        response = self.reset(otp_from_last_email())
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_reset_otp_cannot_be_brute_forced(self):
        self.forgot()
        otp = otp_from_last_email()

        for _ in range(MAX_OTP_ATTEMPTS):
            self.post("/accounts/verify-reset-otp/", {"email": "user@example.com", "otp": wrong_otp(otp)})

        response = self.reset(otp)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_wrong_attempts_count_across_verify_and_reset(self):
        self.forgot()
        otp = otp_from_last_email()

        for _ in range(MAX_OTP_ATTEMPTS - 1):
            self.post("/accounts/verify-reset-otp/", {"email": "user@example.com", "otp": wrong_otp(otp)})
        self.reset(wrong_otp(otp))  # 5th wrong attempt

        response = self.reset(otp)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_email_reset_returns_400_not_500(self):
        response = self.post("/accounts/verify-reset-otp/", {"email": "nobody@example.com", "otp": "123456"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.reset("123456", email="nobody@example.com")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_new_otp_replaces_old_one(self):
        self.forgot()
        first = otp_from_last_email()
        self.make_otp_old(self.user, OTPVerification.OTPType.PASSWORD_RESET)

        self.forgot()
        second = otp_from_last_email()

        if first != second:
            response = self.reset(first)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.reset(second)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_inactive_user_cannot_reset(self):
        self.user.is_active = False
        self.user.save()
        self.forgot()
        self.assertEqual(len(mail.outbox), 0)

    def test_unverified_user_gets_no_reset_email(self):
        self.user.is_email_verified = False
        self.user.save()
        response = self.forgot()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)