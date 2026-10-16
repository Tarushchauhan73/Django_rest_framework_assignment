
from django.conf import settings
from django.core.mail import send_mail


def send_welcome_email(user):
    subject = "Welcome to User Management API"

    message = (
        f"Hello {user.first_name or user.username},\n\n"
        "Welcome! Your account has been created successfully.\n\n"
        f"Your registered email is: {user.email}\n\n"
        "Thank you for registering."
    )

    return send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def send_otp_email(user, otp):
    subject = "Your Account Verification OTP"

    message = (
        f"Hello {user.first_name or user.username},\n\n"
        f"Your verification OTP is: {otp}\n\n"
        "This OTP expires in 5 minutes.\n"
        "Do not share it with anyone."
    )

    return send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
