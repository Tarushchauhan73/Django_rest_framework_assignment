
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
    
class ProjectType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ProjectStatus(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ProjectTaskStatus(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class BaseModel(models.Model):

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created"
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

# User Model

class User(AbstractUser,BaseModel):

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
      
    country = models.CharField(
        max_length=100,
        null=True,
        blank=True,
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

class Client(BaseModel):

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

    

    def __str__(self):
        return f"{self.fname} {self.lname}".strip()



# Project Model

class Project(BaseModel):

    title = models.CharField(max_length=200, unique=True)

    description = models.TextField(
        null=True,
        blank=True,
    )

    type = models.CharField(
        max_length=100,
        default="Other",
    )

    date_of_completion = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=100,
        default="Not Started",
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

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_projects"
    )

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


class ProjectTask(models.Model):

    # Other existing fields...
 
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks_assigned_to"
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks_assigned_by"
    )

  
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("on_hold", "On Hold"),
    ]
    title = models.CharField(
        max_length=200,
        unique=True
        )

    project = models.ForeignKey(
        "users.Project",
        on_delete=models.CASCADE,
        related_name="tasks",
    )

    start_date = models.DateField(
        null=True,
        blank=True
        )

    completion_date = models.DateField(
        null=True,
        blank=True
        )

    deadline_date = models.DateField(
        null=True, 
        blank=True
        )

    status = models.CharField(
    max_length=100,
    default="Pending",
)
    is_deleted = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_project_tasks",
    )

    updated_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="updated_project_task_comments"
)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class ProjectTaskcomment(models.Model):

    project_task = models.ForeignKey(
        ProjectTask,
        on_delete=models.CASCADE,
        related_name="comments",
    )

    project = models.ForeignKey(
        "users.Project",
        on_delete=models.CASCADE,
        related_name="task_comments",
    )

    commented_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="task_comments",
    )

    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comment by {self.commented_by.email if self.commented_by else 'Unknown'} on task {self.project_task.title}"

