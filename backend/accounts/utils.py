import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .models import OTPVerification


OTP_EXPIRY_MINUTES = 10
MAX_OTP_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 60

INVALID_OTP_MESSAGE = "Invalid or expired OTP."
TOO_MANY_ATTEMPTS_MESSAGE = "Too many incorrect attempts. Please request a new OTP."


def generate_otp():
    # Cryptographically secure 6-digit OTP.
    return f"{secrets.randbelow(1_000_000):06d}"


def _create_otp(user, otp_type):
    """
    Create a new hashed OTP for this user.
    Returns the plain OTP (to email it), or None if the user asked
    again within the cooldown time.
    """
    now = timezone.now()

    with transaction.atomic():
        latest = (
            OTPVerification.objects
            .select_for_update()
            .filter(user=user, otp_type=otp_type)
            .order_by("-created_at")
            .first()
        )

        if latest and (now - latest.created_at).total_seconds() < OTP_RESEND_COOLDOWN_SECONDS:
            return None

        # Only one OTP of each type can be active at a time.
        OTPVerification.objects.filter(user=user, otp_type=otp_type).delete()

        otp = generate_otp()
        OTPVerification.objects.create(
            user=user,
            otp=make_password(otp),
            otp_type=otp_type,
            expires_at=now + timedelta(minutes=OTP_EXPIRY_MINUTES),
        )

    return otp


def create_email_otp(user):
    return _create_otp(user, OTPVerification.OTPType.EMAIL_VERIFICATION)


def create_password_reset_otp(user):
    return _create_otp(user, OTPVerification.OTPType.PASSWORD_RESET)


def check_otp(user, otp_type, otp, consume):
    """
    Check an OTP. Returns None if correct, otherwise an error message.

    consume=True  -> delete the OTP after success (one-time use).
    consume=False -> keep it but mark verified (password reset step 1).

    Wrong guesses are saved before returning, so the attempt limit
    cannot be bypassed.
    """
    otp = str(otp or "").strip()
    error = None

    with transaction.atomic():
        record = None
        if user is not None:
            record = (
                OTPVerification.objects
                .select_for_update()
                .filter(user=user, otp_type=otp_type)
                .order_by("-created_at")
                .first()
            )

        if record is None or record.is_expired():
            error = INVALID_OTP_MESSAGE

        elif record.failed_attempts >= MAX_OTP_ATTEMPTS:
            error = TOO_MANY_ATTEMPTS_MESSAGE

        elif not check_password(otp, record.otp):
            record.failed_attempts += 1
            record.save(update_fields=["failed_attempts"])
            error = INVALID_OTP_MESSAGE

        elif consume:
            record.delete()

        else:
            record.is_verified = True
            record.save(update_fields=["is_verified"])

    return error


def blacklist_all_refresh_tokens(user):
    """Log the user out of every device (used after a password reset)."""
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


def send_email_otp(email, otp, purpose="verification"):

    if purpose == "reset":
        subject = "Password Reset OTP"
        action = "password reset"
    else:
        subject = "Email Verification OTP"
        action = "verification"

    message = f"""
Dear User,

Your One Day Job Portal {action} OTP is:

{otp}

This OTP is valid for {OTP_EXPIRY_MINUTES} minutes.
Never share this OTP with anyone.

If you did not request this, please ignore this email.

Regards,
One Day Job Portal Team
"""

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )