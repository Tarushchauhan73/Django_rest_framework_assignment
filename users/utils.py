
import secrets
from datetime import timedelta

from django.utils import timezone


def generate_otp(user, purpose):
    """
    Generate a six-digit OTP, save its purpose and expiry time.
    """
    otp = f"{secrets.randbelow(1000000):06d}"

    user.otp = otp
    user.otp_purpose = purpose
    user.otp_expires_at = timezone.now() + timedelta(minutes=5)

    user.save(
        update_fields=["otp", "otp_purpose", "otp_expires_at"]
    )

    return otp


def verify_otp(user, entered_otp, purpose):
    """
    Check whether the OTP is correct, valid for the purpose,
    and not expired.
    """
    if not user.otp or not user.otp_expires_at:
        return False

    if user.otp_purpose != purpose:
        return False

    if timezone.now() >= user.otp_expires_at:
        return False

    return secrets.compare_digest(user.otp, str(entered_otp))


def clear_otp(user):
    """
    Clear OTP data after successful verification or password reset.
    """
    user.otp = ""
    user.otp_purpose = ""
    user.otp_expires_at = None

    user.save(
        update_fields=["otp", "otp_purpose", "otp_expires_at"]
    )
