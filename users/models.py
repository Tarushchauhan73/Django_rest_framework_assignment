
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from profile import Profile
from django.utils import timezone

# Dynamic Profile Model
class Profile(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.name



# Custom User Model

class User(AbstractUser):

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

    # Username is optional and can be NULL.
    username = models.CharField(
        max_length=150,
        unique=True,
        null=True,
        blank=True,
    )

    email = models.EmailField(
        unique=True,
        blank=False,
        null=False,
    )

    # Profiles are configured dynamically in the database.
    profiles = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )

    date_of_birth = models.DateField(null=True, blank=True)

    gender = models.CharField(
        max_length=30,
        choices=GenderChoices.choices,
        null=True,
        blank=True,
    )

    nationality = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )

    image = models.ImageField(
        upload_to="user_images/",
        null=True,
        blank=True,
    )

    blood_group = models.CharField(
        max_length=3,
        choices=BloodGroupChoices.choices,
        null=True,
        blank=True,
    )

    phone = models.CharField(
        max_length=20,
        null=True,
        blank=True,
    )

    permanent_address = models.TextField(null=True, blank=True)
    current_address = models.TextField(null=True, blank=True)

    emergency_contact_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )

    emergency_contact_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
    )

    emergency_contact_relationship = models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE,
    )

    # OTP and request-limit fields
    attempt = models.PositiveIntegerField(default=0)

    otp_window_started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    blocked_until = models.DateTimeField(
        null=True,
        blank=True,
    )

    otp = models.CharField(max_length=6, blank=True, default="")

    otp_purpose = models.CharField(
        max_length=30,
        choices=OTPPurposeChoices.choices,
        blank=True,
        default="",
    )

    otp_expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.email or f"User {self.pk}"



# Client Model

class Client(models.Model):

    class StatusChoices(models.TextChoices):
        ACTIVE = "Active", "Active"
        INACTIVE = "Inactive", "Inactive"

    fname = models.CharField(max_length=100, blank=True)
    lname = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    contactno = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    email = models.EmailField(
        unique=True,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients_created",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients_updated",
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.fname} {self.lname}".strip()



# Project Model

class Project(models.Model):

    class ProjectType(models.TextChoices):
        WEB = "Web", "Web"
        MOBILE = "Mobile", "Mobile"
        SOFTWARE = "Software", "Software"
        DATA = "Data", "Data"
        OTHER = "Other", "Other"

    class ProjectStatus(models.TextChoices):
        NOT_STARTED = "Not Started", "Not Started"
        IN_PROGRESS = "In Progress", "In Progress"
        COMPLETED = "Completed", "Completed"
        ON_HOLD = "On Hold", "On Hold"
        CANCELLED = "Cancelled", "Cancelled"

    title = models.CharField(max_length=200, unique=True)

    type = models.CharField(
        max_length=20,
        choices=ProjectType.choices,
        default=ProjectType.OTHER,
    )

    date_of_completion = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.NOT_STARTED,
    )

    client = models.ForeignKey(
    "users.Client",
    on_delete=models.SET_NULL,
    related_name="projects",
    null=True,
    blank=True,
)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="managed_projects",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects_created",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects_updated",
    )

    updated_at = models.DateTimeField(auto_now=True)

    is_deleted = models.BooleanField(default=False)

    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects_deleted",
    )

    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

class ProjectAttachement(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(upload_to="project_attachments/")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attachements_uploaded",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachement for {self.project.title} uploaded by {self.uploaded_by.email if self.uploaded_by else 'Unknown'}"

