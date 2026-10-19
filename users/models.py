import secrets
from datetime import timedelta

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):

    class ProfileChoices(models.TextChoices):
        ADMINISTRATOR = "Administrator", "Administrator"
        STANDARD = "Standard", "Standard"
        DEVELOPER = "Developer", "Developer"
        CLIENT = "Client", "Client"
        HUMAN_RESOURCE = "Human Resource", "Human Resource"

    class StatusChoices(models.TextChoices):
        ACTIVE = "Active", "Active"
        INACTIVE = "Inactive", "Inactive"

    class GenderChoices(models.TextChoices):
        MALE = "Male", "Male"
        FEMALE = "Female", "Female"
        OTHER = "Other", "Other"
        PREFER_NOT_TO_SAY = "Prefer not to say", "Prefer not to say"

    class BloodGroupChoices(models.TextChoices):
        A_POSITIVE = "A+", "A+"
        A_NEGATIVE = "A-", "A-"
        B_POSITIVE = "B+", "B+"
        B_NEGATIVE = "B-", "B-"
        AB_POSITIVE = "AB+", "AB+"
        AB_NEGATIVE = "AB-", "AB-"
        O_POSITIVE = "O+", "O+"
        O_NEGATIVE = "O-", "O-"

    class OTPPurposeChoices(models.TextChoices):
        EMAIL_VERIFICATION = "email_verification", "Email Verification"
        PASSWORD_RESET = "password_reset", "Password Reset"

    # User details
    email = models.EmailField(unique=True)

    profiles = models.CharField(
        max_length=20,
        choices=ProfileChoices.choices,
        default=ProfileChoices.STANDARD,
    )

    date_of_birth = models.DateField(null=True, blank=True)

    gender = models.CharField(
        max_length=20,
        choices=GenderChoices.choices,
        blank=True,
    )

    nationality = models.CharField(max_length=100, blank=True)

    image = models.ImageField(
        upload_to="profile_images/",
        null=True,
        blank=True,
    )

    blood_group = models.CharField(
        max_length=3,
        choices=BloodGroupChoices.choices,
        blank=True,
    )

    phone = models.CharField(max_length=20, blank=True)
    permanent_address = models.TextField(blank=True)
    current_address = models.TextField(blank=True)

    emergency_contact_name = models.CharField(
        max_length=100,
        blank=True,
    )

    emergency_contact_number = models.CharField(
        max_length=20,
        blank=True,
    )

    emergency_contact_relationship = models.CharField(
        max_length=50,
        blank=True,
    )

    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE,
    )

    # OTP details stored in the same User model
    otp = models.CharField(
        max_length=6,
        blank=True,
    )

    otp_purpose = models.CharField(
        max_length=30,
        choices=OTPPurposeChoices.choices,
        blank=True,
    )

    otp_created_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    otp_expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    otp_is_verified = models.BooleanField(default=False)

    @classmethod
    def generate_otp(cls, user, purpose):
        """Generate a six-digit OTP valid for five minutes."""

        user.otp = f"{secrets.randbelow(1_000_000):06d}"
        user.otp_purpose = purpose
        user.otp_created_at = timezone.now()
        user.otp_expires_at = timezone.now() + timedelta(minutes=5)
        user.otp_is_verified = False

        user.save(
            update_fields=[
                "otp",
                "otp_purpose",
                "otp_created_at",
                "otp_expires_at",
                "otp_is_verified",
            ]
        )

        return user.otp

    def verify_otp(self, entered_otp, purpose):
        """Check OTP, purpose, expiry, and verification status."""

        if not self.otp:
            return False

        if self.otp_is_verified:
            return False

        if self.otp_purpose != purpose:
            return False

        if not self.otp_expires_at:
            return False

        if timezone.now() >= self.otp_expires_at:
            return False

        if self.otp != entered_otp:
            return False

        self.otp_is_verified = True
        self.save(update_fields=["otp_is_verified"])

        return True

    def clear_otp(self):
        """Remove OTP details after the operation is completed."""

        self.otp = ""
        self.otp_purpose = ""
        self.otp_created_at = None
        self.otp_expires_at = None
        self.otp_is_verified = False

        self.save(
            update_fields=[
                "otp",
                "otp_purpose",
                "otp_created_at",
                "otp_expires_at",
                "otp_is_verified",
            ]
        )

    def __str__(self):
        return self.username
