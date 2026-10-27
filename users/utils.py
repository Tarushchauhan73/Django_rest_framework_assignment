
import secrets
from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import ValidationError


def generate_otp(user, purpose):
    """Generate a six-digit OTP valid for five minutes."""
    otp = f"{secrets.randbelow(1_000_000):06d}"

    user.otp = otp
    user.otp_purpose = purpose
    user.otp_expires_at = timezone.now() + timedelta(minutes=5)

    user.save(
        update_fields=[
            "otp",
            "otp_purpose",
            "otp_expires_at",
        ]
    )

    return otp


def verify_otp(user, entered_otp, purpose):
    """Check whether the OTP is correct, unexpired, and for the right purpose."""
    if not user.otp or not user.otp_expires_at:
        return False

    if user.otp_purpose != purpose:
        return False

    if timezone.now() >= user.otp_expires_at:
        return False

    return secrets.compare_digest(user.otp, str(entered_otp))


def clear_otp(user):
    """Remove the OTP after successful verification."""
    user.otp = ""
    user.otp_purpose = ""
    user.otp_expires_at = None

    user.save(
        update_fields=[
            "otp",
            "otp_purpose",
            "otp_expires_at",
        ]
    )


def check_otp_request_limit(user):
    """
    Allow a maximum of three OTP requests in a 12-hour window.
    The limit is shared across OTP-sending endpoints.
    """

    now = timezone.now()

    error_message = (
        "You have exceeded the maximum number of OTP requests. "
        "Please try again after 12 hours."
    )

    # If the user is blocked, reject the request.
    if user.blocked_until and now < user.blocked_until:
        raise ValidationError({"detail": error_message})

    # Start a new 12-hour window if the previous window has expired.
    if (
        user.otp_window_started_at is None
        or now >= user.otp_window_started_at + timedelta(hours=12)
    ):
        user.attempt = 0
        user.otp_window_started_at = now
        user.blocked_until = None

    # If three requests have already been made, block further requests.
    if user.attempt >= 3:
        user.blocked_until = now + timedelta(hours=12)

        user.save(update_fields=["blocked_until"])

        raise ValidationError({"detail": error_message})

    # Count this OTP request.
    user.attempt += 1

    user.save(
        update_fields=[
            "attempt",
            "otp_window_started_at",
            "blocked_until",
        ]
    )
