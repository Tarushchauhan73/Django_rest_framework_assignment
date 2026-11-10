
from urllib import request
from urllib import request
from xml.dom.minidom import Attr

from django.db.models import Value
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Client, Profile, Project, ProjectAttachement 
from .models import Project, ProjectAttachement, Client, User
from .models import ProjectTask, ProjectTaskcomment
User = get_user_model()

class ProfileSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="name", read_only=True)

    class Meta:
        model = Profile
        fields = ["id", "role", "is_active", "is_default"]

class UserDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
        ]
        
class ClientSerializer(serializers.ModelSerializer):

    created_by = UserDetailSerializer(read_only=True)
    updated_by = UserDetailSerializer(read_only=True)

    class Meta:
        model = Client
        fields = "__all__"
        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "updated_by",
            "updated_at",
        ]

    def validate(self, attrs):
        for field in ["fname", "lname", "email"]:
            if self.instance is not None and field not in attrs:
                continue

            value = attrs.get(field)

            if value is None or (
                isinstance(value, str) and not value.strip()
            ):
                raise serializers.ValidationError({
                    field: f"{field.replace('_', ' ').capitalize()} is required."
                })

        return attrs

class UserSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            if self.instance:
                self.fields["email"].required = False

    username = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        validators=[],
    )

    email = serializers.EmailField(
    required=True,
    allow_blank=False,
    allow_null=False
)

    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=False,
        style={"input_type": "password"},
    )

    profile = serializers.CharField(required=False, write_only=True)

    profile_id = serializers.PrimaryKeyRelatedField(
        queryset=Profile.objects.filter(is_active=True),
        source="profiles",
        write_only=True,
        required=False,
        allow_null=True,
    )
    profiles_details = serializers.SerializerMethodField()

    def get_profiles_details(self, obj):
        if obj.profiles:
            return {
                "id": obj.profiles.id,
                "role": obj.profiles.name,
                "is_active": obj.profiles.is_active,
                "is_default": obj.profiles.is_default
            }

        return None

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "password",
            "profiles",
            "profile",
            "profiles_details",
            "profile_id",
            "date_of_birth",
            "gender",
            "nationality",
            "image",
            "blood_group",
            "phone",
            "permanent_address",
            "current_address",
            "emergency_contact_name",
            "emergency_contact_number",
            "emergency_contact_relationship",
            "status",
        ]
        read_only_fields = ["id"]

    def validate_manager(self, value):

        if value.status != "Active":
            raise serializers.ValidationError(
                "Cannot assign an inactive or soft-deleted user."
            )

        if value.profiles is None:
            raise serializers.ValidationError(
                "This user has no assigned role. Assign a Manager role first."
            )

        if value.profiles.name.strip().lower() != "manager":
            raise serializers.ValidationError(
                "Projects can only be assigned to users with Manager profiles."
            )

        return value
    def validate_profile(self, value):

        if self.instance and self.instance.profiles:
            if self.instance.profiles.is_default:
                raise serializers.ValidationError(
                    "Default profiles cannot be edited."
                )

        profile = Profile.objects.filter(role__iexact=value).first()

        if not profile:
            raise serializers.ValidationError("Profile does not exist.")

        return profile
        
    def create(self, validated_data):
        # Get the profile selected by the user.
        profile = validated_data.pop("profiles", None)

        if profile is None:
            profile = Profile.objects.filter(
                name="Standard",
                is_active=True,
                is_default=True,
            ).first()

            if profile is None:
                raise serializers.ValidationError({
                    "profile_id": "Default Standard profile not found."
                })

        # Generate password if not provided.
        password = validated_data.pop("password", None)

        if not password:
            email = validated_data.get("email", "")
            password = email.split("@")[0] + "@123"

        user = User(**validated_data)
        user.profiles = profile
        user.set_password(password)
        user.save()

        return user

    
def update(self, instance, validated_data):
    password = validated_data.pop("password", None)

    # Handle profile update
    profile = validated_data.pop("profile", None)

    if profile is not None:
        if instance.profiles and instance.profiles.is_default:
            raise serializers.ValidationError({
                "profile": "Default profiles cannot be edited."
            })

        instance.profiles = profile

    # Preserve the existing username if it wasn't supplied.
    if "username" not in validated_data:
        validated_data["username"] = instance.username

    new_username = validated_data.get("username")

    if new_username == "":
        new_username = None
        validated_data["username"] = None

    # Check whether another user already has this username.
    if new_username is not None:
        username_exists = User.objects.filter(
            username=new_username
        ).exclude(pk=instance.pk).exists()

        if username_exists:
            raise serializers.ValidationError({
                "username": "This username is already in use."
            })

    for field, value in validated_data.items():
        setattr(instance, field, value)

    if password:
        instance.set_password(password)

    instance.save()
    return instance


class ProjectDetailsSerializer(serializers.ModelSerializer):


    class Meta:
        model = Project
        fields = [
            "id",
            "title",
            "status",
            
        ]

    def get_client_name(self, obj):
        return f"{obj.client.fname} {obj.client.lname}"

    def get_manager_name(self, obj):
        return f"{obj.manager.first_name} {obj.manager.last_name}"



class AssignedUserDetailsSerializer(serializers.ModelSerializer):

    profile = serializers.CharField(
        source="profiles.name",
        read_only=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "profile"
        ]

class ProjectTaskSerializer(serializers.ModelSerializer):

    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(),
        required=False
)

    project_details = ProjectDetailsSerializer(
        source="project",
        read_only=True
    )

    
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False
    )

    assigned_to_details = AssignedUserDetailsSerializer(
        source="assigned_to",
        read_only=True
    )

    assigned_by = serializers.PrimaryKeyRelatedField(
        read_only=True
    )

    assigned_by_details = AssignedUserDetailsSerializer(
        source="assigned_by",
        read_only=True
    )

    created_by = serializers.PrimaryKeyRelatedField(
        read_only=True
    )

    created_by_details = AssignedUserDetailsSerializer(
        source="created_by",
        read_only=True
    )

    updated_by = serializers.PrimaryKeyRelatedField(
        read_only=True
    )

    updated_by_details = AssignedUserDetailsSerializer(
        source="updated_by",
        read_only=True
    )

    def validate_assigned_to(self, value):

        if value.profiles is None:
            raise serializers.ValidationError(
                "This user does not have an assigned profile."
            )

        allowed_profiles = ["developer", "teamleader"]

        if value.profiles.name.strip().lower() not in allowed_profiles:
            raise serializers.ValidationError(
                "Tasks can only be assigned to Developers or Team Leaders."
            )

        return value

    def validate(self, attrs):

        start_date = attrs.get(
            "start_date",
            getattr(self.instance, "start_date", None)
        )

        deadline_date = attrs.get(
            "deadline_date",
            getattr(self.instance, "deadline_date", None)
        )

        completion_date = attrs.get(
            "completion_date",
            getattr(self.instance, "completion_date", None)
        )

        if start_date and deadline_date:
            if deadline_date < start_date:
                raise serializers.ValidationError({
                    "deadline_date":
                    "Deadline cannot be before the start date."
                })

        if completion_date and start_date:
            if completion_date < start_date:
                raise serializers.ValidationError({
                    "completion_date":
                    "Completion date cannot be before the start date."
                })

        return attrs

    class Meta:
        model = ProjectTask

        fields = [
            "id",
            "title",

            "project",
            "project_details",

            "assigned_to",
            "assigned_to_details",

            "assigned_by",
            "assigned_by_details",

            "start_date",
            "completion_date",
            "deadline_date",
            "status",

            "created_by",
            "created_by_details",

            "updated_by",
            "updated_by_details",

            "created_at",
            "updated_at"
        ]

        read_only_fields = [
            "id",
            "assigned_by",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at"
        ]


class ProjectTaskDetailsSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProjectTask
        fields = [
            "id",
            "title",
            "start_date",
            "completion_date",
            "deadline_date",
            "status"
        ]
class ProjectTaskCommentSerializer(serializers.ModelSerializer):

    commented_by = serializers.PrimaryKeyRelatedField(read_only=True)

    commented_by_name = serializers.SerializerMethodField()

    project_task = serializers.PrimaryKeyRelatedField(
        queryset=ProjectTask.objects.all()
    )

    project_task_details = ProjectTaskDetailsSerializer(
        source="project_task",
        read_only=True
    )

    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all()
    )

    project_details = ProjectDetailsSerializer(
        source="project",
        read_only=True
    )

    def get_commented_by_name(self, obj):
        if obj.commented_by:
            return (
                f"{obj.commented_by.first_name} "
                f"{obj.commented_by.last_name}"
            )
        return None

    def validate(self, attrs):
        task = attrs.get(
            "project_task",
            getattr(self.instance, "project_task", None)
        )

        project = attrs.get(
            "project",
            getattr(self.instance, "project", None)
        )

        if task and project and task.project_id != project.id:
            raise serializers.ValidationError(
                "The selected project does not belong to this task."
            )

        return attrs

    class Meta:
        model = ProjectTaskcomment

        fields = [
            "id",
            "commented_by",
            "commented_by_name",
            "comment",
            "created_at",
            "updated_at",
            "project_task",
            "project_task_details",
            "project",
            "project_details",
            
        ]

        read_only_fields = [
            "commented_by",
            "created_at",
            "updated_at"
        ]


class SendOTPSerializer(serializers.Serializer):

    email = serializers.EmailField(
        required=True,
        allow_blank=False,
    )

    def validate_email(self, value):
        value = value.strip().lower()

        if not User.objects.filter(
            email__iexact=value,
            status="Active",
        ).exists():
            raise serializers.ValidationError(
                "No active user found with this email."
            )

        return value

from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
        ]
class ClientRelatedField(serializers.RelatedField):
    def to_internal_value(self, value):
        if isinstance(value, int) or (
            isinstance(value, str) and value.isdigit()
        ):
            client = Client.objects.filter(pk=int(value)).first()
        elif isinstance(value, str) and "@" in value:
            client = Client.objects.filter(
                email__iexact=value.strip()
            ).first()
        elif isinstance(value, str):
            parts = value.strip().split(maxsplit=1)

            if len(parts) == 2:
                client = Client.objects.filter(
                    fname__iexact=parts[0],
                    lname__iexact=parts[1],
                ).first()
            else:
                matches = Client.objects.filter(
                    fname__iexact=value.strip()
                )
                if matches.count() > 1:
                    raise serializers.ValidationError(
                        "Multiple clients match this name. Use the client ID or email."
                    )
                client = matches.first()
        else:
            client = None

        if client is None:
            raise serializers.ValidationError(
                "Client not found. Provide a valid ID, email, or name."
            )

        return client

    def to_representation(self, client):
        return {
            "id": client.id,
            "first_name": client.fname,
            "last_name": client.lname,
            "email": client.email,
        }


class ManagerRelatedField(serializers.RelatedField):
    def to_internal_value(self, value):
        if isinstance(value, int) or (
            isinstance(value, str) and value.isdigit()
        ):
            manager = User.objects.filter(pk=int(value)).first()
        elif isinstance(value, str) and "@" in value:
            manager = User.objects.filter(
                email__iexact=value.strip()
            ).first()
        elif isinstance(value, str):
            value = value.strip()
            matches = User.objects.filter(
                username__iexact=value
            )

            if not matches.exists():
                parts = value.split(maxsplit=1)
                if len(parts) == 2:
                    matches = User.objects.filter(
                        first_name__iexact=parts[0],
                        last_name__iexact=parts[1],
                    )
                else:
                    matches = User.objects.filter(
                        first_name__iexact=value
                    )

            if matches.count() > 1:
                raise serializers.ValidationError(
                    "Multiple users match this name. Use the manager ID or email."
                )

            manager = matches.first()
        else:
            manager = None

        if manager is None:
            raise serializers.ValidationError(
                "Manager not found. Provide a valid ID, email, username, or name."
            )

        return manager

    def to_representation(self, manager):
        return {
            "id": manager.id,
            "username": manager.username,
            "first_name": manager.first_name,
            "last_name": manager.last_name,
            "email": manager.email,
            "role": manager.profiles.name if manager.profiles else None,
        }



class ProjectAttachementSerializer(serializers.ModelSerializer):

    file = serializers.SerializerMethodField()

    class Meta:
        model = ProjectAttachement
        fields = [
            "id",
            "file",
            "uploaded_by",
            "uploaded_at",
        ]

    def get_file(self, obj):
        if not obj.file:
            return None

        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(obj.file.url)

        return obj.file.url

        


class ProjectSerializer(serializers.ModelSerializer):

    client = ClientRelatedField(
        queryset=Client.objects.all(),
        required=False,
        allow_null=True,
    )

    manager = ManagerRelatedField(
        queryset=User.objects.all(),
        required=True,
        allow_null=False
)
    

    created_by = UserDetailSerializer(read_only=True)
    updated_by = UserDetailSerializer(read_only=True)

    attachments = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = Project
        fields = "__all__"

    def create(self, validated_data):
        # Get uploaded files from validated data
        attachments = validated_data.pop("attachments", [])

        # Get request from serializer context
        request = self.context.get("request")

       
        if request:
            attachments = request.FILES.getlist("attachments") or attachments

      
        project = Project.objects.create(**validated_data)

        for uploaded_file in attachments:
            ProjectAttachement.objects.create(
                project=project,
                file=uploaded_file,
                uploaded_by=request.user if request else None
            )

        return project

    def to_representation(self, instance):
        data = super().to_representation(instance)

        data["attachments"] = ProjectAttachementSerializer(
            instance.attachments.all(),
            many=True,
           context=self.context,
        ).data

        return data

    def update(self, instance, validated_data):
     request = self.context.get("request")

     
     attachment_id = request.data.get("attachments_id") if request else None

     # Get newly uploaded files
     files = validated_data.pop("attachments", [])

     if request:
        files = files or request.FILES.getlist("attachments")

    
     if attachment_id:
        try:
            attachment = instance.attachments.get(id=attachment_id)
        except ProjectAttachement.DoesNotExist:
            raise serializers.ValidationError({
                "attachments_id": "Attachment not found in this project."
            })

        attachment.file.delete(save=False)
        attachment.delete()

  
     for field, value in validated_data.items():
        setattr(instance, field, value)

     instance.save()

  
     for uploaded_file in files:
        ProjectAttachement.objects.create(
            project=instance,
            file=uploaded_file,
            uploaded_by=request.user if request else None,
        )

     return instance



    
    def to_representation(self, instance):
        data = super().to_representation(instance)

        data["attachments"] = ProjectAttachementSerializer(
            instance.attachments.all(),
            many=True,
            context=self.context,
        ).data

        return data
    
    def validate_manager(self, value):

        if value.status != "Active":
            raise serializers.ValidationError(
                "Cannot assign an inactive or soft-deleted user."
            )

        if value.profiles is None:
            raise serializers.ValidationError(
                "This user has no assigned role."
            )

        allowed_profiles = [
            "manager",
           
        ]

        if value.profiles.name.strip().lower() not in allowed_profiles:
            raise serializers.ValidationError(
                "Projects can only be assigned to users with Manager profiles."
            )

        return value
class ProjectDetailsSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    manager_name = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "title",
            "status",
           
        ]

    def get_client_name(self, obj):
        return f"{obj.client.fname} {obj.client.lname}"

    def get_manager_name(self, obj):
        return f"{obj.manager.first_name} {obj.manager.last_name}"

              
