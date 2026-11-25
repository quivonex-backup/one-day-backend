
import re
import secrets
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import LoginOTPChallenge


OTP_EXPIRY_MINUTES = 5
MAX_OTP_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 60


def normalize_otp_identifier(identifier, channel):
    # Clean and validate the email or mobile number
    identifier = str(identifier or "").strip()

    if channel == LoginOTPChallenge.Channel.EMAIL:
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError as DjangoValidationError

        identifier = identifier.lower()

        try:
            validate_email(identifier)
        except DjangoValidationError:
            raise ValidationError({
                "identifier": "Enter a valid email address."
            })

    elif channel == LoginOTPChallenge.Channel.MOBILE:
        # Accept a 10-digit Indian mobile number
        if not re.fullmatch(r"[6-9]\d{9}", identifier):
            raise ValidationError({
                "identifier": "Enter a valid 10-digit mobile number."
            })

    else:
        raise ValidationError({
            "channel": "Choose EMAIL or MOBILE."
        })

    return identifier


def create_login_otp(identifier, channel):
    # Validate the selected contact method
    identifier = normalize_otp_identifier(identifier, channel)

    now = timezone.now()

    with transaction.atomic():
        # Lock existing OTP requests for this identifier
        latest = (
            LoginOTPChallenge.objects
            .select_for_update()
            .filter(identifier=identifier, channel=channel)
            .order_by("-created_at")
            .first()
        )

        # Stop repeated OTP requests within 60 seconds
        if latest and (now - latest.created_at).total_seconds() < OTP_RESEND_COOLDOWN_SECONDS:
            raise ValidationError({
                "otp": "Please wait 60 seconds before requesting another OTP."
            })

        # Generate a secure six-digit OTP
        otp = f"{secrets.randbelow(1000000):06d}"

        # Expire previous unused OTP requests
        LoginOTPChallenge.objects.filter(
            identifier=identifier,
            channel=channel,
            is_used=False
        ).update(is_used=True)

        # Store only the hashed OTP
        LoginOTPChallenge.objects.create(
            identifier=identifier,
            channel=channel,
            otp_hash=make_password(otp),
            expires_at=now + timedelta(minutes=OTP_EXPIRY_MINUTES)
        )

    return otp



def verify_login_otp(identifier, channel, otp):

    # Validate email/mobile and OTP format
    identifier = normalize_otp_identifier(identifier, channel)
    otp = str(otp or "").strip()

    if not re.fullmatch(r"\d{6}", otp):
        raise ValidationError({
            "otp": "Enter a valid six-digit OTP."
        })

    error_message = None

    with transaction.atomic():

        # Lock the latest unused OTP
        challenge = (
            LoginOTPChallenge.objects
            .select_for_update()
            .filter(
                identifier=identifier,
                channel=channel,
                is_used=False
            )
            .order_by("-created_at")
            .first()
        )

        if challenge is None or challenge.is_expired():
            error_message = "OTP is invalid or expired."

        elif challenge.failed_attempts >= MAX_OTP_ATTEMPTS:
            error_message = (
                "Too many incorrect attempts. Request a new OTP."
            )

        elif not check_password(otp, challenge.otp_hash):

            # Save incorrect attempts before returning an error
            challenge.failed_attempts += 1

            if challenge.failed_attempts >= MAX_OTP_ATTEMPTS:
                challenge.is_used = True

            challenge.save(
                update_fields=["failed_attempts", "is_used"]
            )

            error_message = "Incorrect OTP."

        else:
            # OTP can be used only once
            challenge.is_used = True
            challenge.save(update_fields=["is_used"])

    # Raise the error after the transaction is committed
    if error_message:
        raise ValidationError({
            "otp": error_message
        })

    return identifier