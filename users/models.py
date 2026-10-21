
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class User(AbstractUser):

    class ProfileChoices(models.TextChoices):
        ADMINISTRATOR = "Administrator", "Administrator"
        STANDARD = "Standard", "Standard"
        DEVELOPER = "Developer", "Developer"
        CLIENT = "Client", "Client"
        HUMAN = "Human", "Human"

    class GenderChoices(models.TextChoices):
        MALE = "Male", "Male"
        FEMALE = "Female", "Female"
        OTHER = "Other", "Other"

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

    # User details
    email = models.EmailField(unique=True)
    profile = models.CharField(
        max_length=20,
        choices=ProfileChoices.choices,
        default=ProfileChoices.STANDARD
    )
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=GenderChoices.choices,
        blank=True
    )
    nationality = models.CharField(max_length=100, blank=True)
    image = models.ImageField(
        upload_to="user_images/",
        null=True,
        blank=True
    )
    blood_group = models.CharField(
        max_length=3,
        choices=BloodGroupChoices.choices,
        blank=True
    )
    phone = models.CharField(max_length=20, blank=True)
    permanent_address = models.TextField(blank=True)
    current_address = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_number = models.CharField(max_length=20, blank=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True)

    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE
    )

    # OTP data storage only: OTP logic is handled in views.py
    otp = models.CharField(max_length=6, blank=True)
    otp_purpose = models.CharField(
        max_length=30,
        choices=OTPPurposeChoices.choices,
        blank=True
    )
    otp_expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.username


class Client(models.Model):
    fname = models.CharField(max_length=100)
    lname = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

    # Additional client details
    country = models.CharField(max_length=100, blank=True)
    contactno = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    status = models.CharField(max_length=20, default="Active")

    # Audit tracking
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
        return f"{self.fname} {self.lname}"
