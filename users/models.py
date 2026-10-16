from django.db import models
from django.contrib.auth.models import AbstractUser


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
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_number = models.CharField(max_length=20, blank=True)
    emergency_contact_relationship = models.CharField(
        max_length=50,
        blank=True,
    )
    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE,
    )

    def __str__(self):
        return self.username

          