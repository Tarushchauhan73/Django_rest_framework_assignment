
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    class ProfileChoices(models.TextChoices):
        ADMINISTRATOR = "Administrator", "Administrator"
        STANDARD = "Standard", "Standard"
        DEVELOPER = "Developer", "Developer"
        CLIENT = "Client", "Client"
        HUMAN_RESOURCE = "Human Resource", "Human Resource"

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

    class StatusChoices(models.TextChoices):
        ACTIVE = "Active", "Active"
        INACTIVE = "Inactive", "Inactive"

    class OTPPurposeChoices(models.TextChoices):
        EMAIL_VERIFICATION = "email_verification", "Email Verification"
        PASSWORD_RESET = "password_reset", "Password Reset"

    # User profile fields
    email = models.EmailField(
        unique=True,
        blank=True,
        null=True
    )

    profiles = models.CharField(
        max_length=30,
        choices=ProfileChoices.choices,
        blank=True,
        null=True
    )

    date_of_birth = models.DateField(
        blank=True,
        null=True
    )

    gender = models.CharField(
        max_length=30,
        choices=GenderChoices.choices,
        blank=True,
        null=True
    )

    nationality = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    image = models.ImageField(
        upload_to="user_images/",
        blank=True,
        null=True
    )

    blood_group = models.CharField(
        max_length=3,
        choices=BloodGroupChoices.choices,
        blank=True,
        null=True
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    permanent_address = models.TextField(
        blank=True,
        null=True
    )

    current_address = models.TextField(
        blank=True,
        null=True
    )

    emergency_contact_name = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    emergency_contact_number = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    emergency_contact_relationship = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE
    )

    # OTP fields: OTP processing is handled in utils.py/views.py
    attempt = models.PositiveIntegerField(default=0)

    otp_window_started_at = models.DateTimeField(
        blank=True,
        null=True
    )

    blocked_until = models.DateTimeField(
        blank=True,
        null=True
    )

    otp = models.CharField(
        max_length=6,
        blank=True,
        default=""
    )

    otp_purpose = models.CharField(
        max_length=30,
        choices=OTPPurposeChoices.choices,
        blank=True,
        default=""
    )

    otp_expires_at = models.DateTimeField(
        blank=True,
        null=True
    )

    def __str__(self):
        return self.username


class Client(models.Model):

    class StatusChoices(models.TextChoices):
        ACTIVE = "Active", "Active"
        INACTIVE = "Inactive", "Inactive"

    fname = models.CharField(
        max_length=100,
        blank=True
    )

    lname = models.CharField(
        max_length=100,
        blank=True
    )

    country = models.CharField(
        max_length=100,
        blank=True
    )

    contactno = models.CharField(
        max_length=20,
        blank=True
    )

    address = models.TextField(
        blank=True
    )

    email = models.EmailField(
        unique=True,
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE
    )

    # Audit fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients_created"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients_updated"
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.fname} {self.lname}".strip()
