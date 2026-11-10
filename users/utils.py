
import secrets
from datetime import timedelta
import logging
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings

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

logger = logging.getLogger(__name__)


def send_project_notifications(project):

    results = {
        "client": {},
        "manager": {},
    }

    # Client notification
    if project.client and project.client.email:
        try:
            manager = project.manager

            manager_name = (
                manager.get_full_name() or manager.username
                if manager else "Not assigned"
            )

            manager_email = (
                manager.email if manager else "Not available"
            )

            message = f"""
Hello {project.client.fname},

A new project has been assigned to you.

Project Title: {project.title}
Status: {project.status}
Description: {project.description or "Not provided"}

Manager: {manager_name}
Manager Email: {manager_email}

Regards,
Team
"""

            sent = send_mail(
                subject=f"New Project Assigned: {project.title}",
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[project.client.email],
                fail_silently=False,
            )

            results["client"] = {
                "recipient": project.client.email,
                "status": "submitted" if sent == 1 else "failed",
                "description_included": bool(project.description),
            }

        except Exception as error:
            logger.exception("Client notification failed.")
            results["client"] = {
                "recipient": project.client.email,
                "status": "failed",
                "error": str(error),
            }
    else:
        results["client"] = {"status": "skipped", "reason": "No client email"}

    # Manager notification
    if project.manager and project.manager.email:
        try:
            client_name = (
                f"{project.client.fname} {project.client.lname}"
                if project.client else "Not assigned"
            )

            client_email = (
                project.client.email if project.client else "Not available"
            )

            message = f"""
Hello {project.manager.get_full_name() or project.manager.username},

A new project has been assigned to you.

Project Title: {project.title}
Status: {project.status}
Description: {project.description or "Not provided"}

client: {client_name}
client Email: {client_email}

Regards,
Team
"""

            sent = send_mail(
                subject=f"New Project Assigned: {project.title}",
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[project.manager.email],
                fail_silently=False,
            )

            results["manager"] = {
                "recipient": project.manager.email,
                "status": "submitted" if sent == 1 else "failed",
                "description_included": bool(project.description),
            }

        except Exception as error:
            logger.exception("Manager notification failed.")
            results["manager"] = {
                "recipient": project.manager.email,
                "status": "failed",
                "error": str(error),
            }
    else:
        results["manager"] = {"status": "skipped", "reason": "No manager email"}

    return results