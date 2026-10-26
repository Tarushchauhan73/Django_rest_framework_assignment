
import secrets
from datetime import timedelta

from django.utils import timezone


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
