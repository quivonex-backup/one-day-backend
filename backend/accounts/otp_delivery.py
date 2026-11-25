
from django.conf import settings
from django.core.mail import send_mail
from rest_framework.exceptions import ValidationError

from .models import LoginOTPChallenge


def send_otp_email(email, otp):
    # Send OTP to the user's email
    subject = "OneDayWork - Your Verification OTP"

    message = (
        f"Your OneDayWork verification OTP is {otp}.\n\n"
        "This OTP is valid for 5 minutes.\n"
        "Do not share this OTP with anyone."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )


def send_otp_mobile(mobile_number, otp):
    # SMS gateway integration is required
    raise ValidationError({
        "mobile": "Mobile OTP service is not configured yet."
    })


def deliver_login_otp(identifier, channel, otp):
    # Send OTP using the selected method
    if channel == LoginOTPChallenge.Channel.EMAIL:
        send_otp_email(identifier, otp)

    elif channel == LoginOTPChallenge.Channel.MOBILE:
        send_otp_mobile(identifier, otp)

    else:
        raise ValidationError({
            "channel": "Invalid OTP delivery method."
        })
