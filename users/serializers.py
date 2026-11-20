
from urllib import request
from urllib import request
from xml.dom.minidom import Attr

from django.db.models import Value
from rest_framework import serializers
from django.contrib.auth import get_user_model

import re
from .models import Client, Profile, Project, ProjectAttachement 
from .models import Project, ProjectAttachement, Client, User
from .models import ProjectTask, ProjectTaskcomment
User = get_user_model()


class StrictStringField(serializers.CharField):

    def to_internal_value(self, data):

        if not isinstance(data, str):
            raise serializers.ValidationError(
                "Please enter a valid string, not a number."
            )

        value = super().to_internal_value(data)

        if value.isdigit():
            raise serializers.ValidationError(
                "Please enter a valid string, not a number."
            )

        return value





class ProfileSerializer(serializers.ModelSerializer):

    role = StrictStringField(
        source="name",
        required=True,
        allow_null=False,
        allow_blank=False
    )

    def validate_role(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Role cannot be empty."
            )

        if value.lower() == "null":
            raise serializers.ValidationError(
                "Role cannot be null."
            )

        # Only alphabets and spaces are allowed
        if not re.fullmatch(r"[A-Za-z ]+", value):
            raise serializers.ValidationError(
                "Role can contain only alphabets and spaces."
            )

        existing_profile = Profile.objects.filter(
            name__iexact=value
        )

        if self.instance:
            existing_profile = existing_profile.exclude(
                id=self.instance.id
            )

        if existing_profile.exists():
            raise serializers.ValidationError(
                "This role already exists."
            )

        return value

    class Meta:
        model = Profile
        fields = ["id", "role", "is_active", "is_default"]

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
        


from django.utils.text import slugify


class OldClientSerializer(serializers.ModelSerializer):

    created_by = UserDetailSerializer(read_only=True)
    updated_by = UserDetailSerializer(read_only=True)

    class Meta:
        model = Client
        fields = [
            "id",
            "fname",
            "lname",
            "country",
            "contactno",
            "address",
            "email",
            "status",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        
class ClientSerializer(serializers.ModelSerializer):

    fname = serializers.CharField(source="first_name")
    lname = serializers.CharField(source="last_name")

    contactno = serializers.CharField(
        source="phone",
        required=False,
        allow_blank=True
    )

    address = serializers.CharField(
        source="permanent_address",
        required=False,
        allow_blank=True
    )

    created_by = UserDetailSerializer(read_only=True)
    updated_by = UserDetailSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "fname",
            "lname",
            "country",
            "contactno",
            "address",
            "email",
            "status",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        for field in ["first_name", "last_name", "email"]:
            if self.instance is not None and field not in attrs:
                continue

            value = attrs.get(field)

            if value is None or (
                isinstance(value, str) and not value.strip()
            ):
                error_field = {
                    "first_name": "fname",
                    "last_name": "lname",
                    "email": "email",
                }[field]

                raise serializers.ValidationError({
                    error_field: f"{error_field.capitalize()} is required."
                })

        return attrs

    def create(self, validated_data):

        client_profile = Profile.objects.get(name="client")
        validated_data["profiles"] = client_profile

        # Generate a unique username automatically
        base_username = slugify(
            validated_data["email"].split("@")[0]
        ) or "client"

        username = base_username[:150]
        count = 1

        while User.objects.filter(username=username).exists():
            suffix = f"_{count}"
            username = base_username[:150 - len(suffix)] + suffix
            count += 1

        validated_data["username"] = username

        # Create account without an active password
        user = User.objects.create(**validated_data)
        user.set_unusable_password()
        user.save()

        return user


class AssignedUserDetailsSerializer(serializers.ModelSerializer):

    profile = serializers.SerializerMethodField()

    def get_profile(self, obj):
        return obj.profiles.name if obj.profiles else None

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "profile"
        ]


class UserSerializer(serializers.ModelSerializer):
    first_name = StrictStringField(required=False)
    last_name = StrictStringField(required=False)

    def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            if self.instance:
                self.fields["email"].required = False

    created_by = AssignedUserDetailsSerializer(read_only=True)

    updated_by = AssignedUserDetailsSerializer(read_only=True)
    
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

    profile = serializers.CharField(
    required=False,
    write_only=True
)

    profile_id = serializers.PrimaryKeyRelatedField(
        queryset=Profile.objects.filter(is_active=True),
        source="profiles",
        write_only=True,
        required=False,
        allow_null=True,
    )

    profiles = serializers.SerializerMethodField()

    def get_profiles(self, obj):
        if obj.profiles:
            return {
                "id": obj.profiles.id,
                "role": obj.profiles.name,
                "is_active": obj.profiles.is_active,
                "is_default": obj.profiles.is_default,
            }

        return None

    def validate_email(self, value):

        value = value.strip().lower()

        existing_user = User.objects.filter(email__iexact=value)

        if self.instance:
            existing_user = existing_user.exclude(id=self.instance.id)

        if existing_user.exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )

        return value
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
            "profile_id",
            "date_of_birth",
            "gender",
            "nationality",
            "image",
            "blood_group",
            "phone",
            "permanent_address",
            "country",
            "current_address",
            "emergency_contact_name",
            "emergency_contact_number",
            "emergency_contact_relationship",
            "status",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
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

        if not isinstance(value, str) or not value.strip():
            raise serializers.ValidationError(
                "Role must contain a valid string value."
            )

        value = value.strip()

        if value.isdigit():
            raise serializers.ValidationError(
                "Role must contain a string value, not a number."
            )

        if self.instance and self.instance.profiles:
            if self.instance.profiles.is_default:
                raise serializers.ValidationError(
                    "Default profiles cannot be edited."
                )

        profile = Profile.objects.filter(
            name__iexact=value,
            is_active=True
        ).first()

        if not profile:
            raise serializers.ValidationError(
                "Profile does not exist."
            )

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
            email = validated_data.get("email", "").strip().lower()
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
class NestedProjectField(serializers.PrimaryKeyRelatedField):

    def to_representation(self, value):
        project = Project.objects.get(pk=value.pk)
        return ProjectDetailsSerializer(project).data

class NestedUserField(serializers.PrimaryKeyRelatedField):

    def to_representation(self, value):
        user = User.objects.get(pk=value.pk)
        return AssignedUserDetailsSerializer(user).data
    
class ProjectTaskSerializer(serializers.ModelSerializer):

    title = StrictStringField()

    project = NestedProjectField(
        queryset=Project.objects.all(),
        required=False
    )

    assigned_to = NestedUserField(
        queryset=User.objects.all(),
        required=False
    )

    assigned_by = AssignedUserDetailsSerializer(
        read_only=True
    )

    created_by = AssignedUserDetailsSerializer(
        read_only=True
    )

    updated_by = AssignedUserDetailsSerializer(
        read_only=True
    )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        
        if self.instance:
            self.fields["title"].required = False

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
    def validate_title(self, value):

        value = value.strip()

        existing_task = ProjectTask.objects.filter(
            title__iexact=value
        )

        if self.instance:
            existing_task = existing_task.exclude(
                id=self.instance.id
            )

        if existing_task.exists():
            raise serializers.ValidationError(
                "A task with this title already exists."
            )

        return value
    
    
    def validate_status(self, value):
        from .models import ProjectTaskStatus

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Task status cannot be empty."
            )

        task_status = ProjectTaskStatus.objects.filter(
            name__iexact=value
        ).first()

        if task_status:
            if not task_status.is_active:
                raise serializers.ValidationError(
                    "This task status is inactive."
                )

            return task_status.name

        task_status = ProjectTaskStatus.objects.create(
            name=value,
            is_active=True
        )

        return task_status.name

    
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
            "assigned_to",
            "assigned_by",
            "start_date",
            "completion_date",
            "deadline_date",
            "status",
            "created_by",
            "updated_by",
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

class NestedProjectTaskField(serializers.PrimaryKeyRelatedField):

    def to_representation(self, value):
        task = ProjectTask.objects.get(pk=value.pk)
        return ProjectTaskDetailsSerializer(task).data
    


class ProjectTaskCommentSerializer(serializers.ModelSerializer):

    comment = StrictStringField()

    commented_by = AssignedUserDetailsSerializer(read_only=True),


    project_task = NestedProjectTaskField(
        queryset=ProjectTask.objects.all(),
        required=False
    )

    project = NestedProjectField(
        queryset=Project.objects.all(),
        required=False
    )

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
            "comment",
            "created_at",
            "updated_at",
            "project_task",
            "project",
        ]

        read_only_fields = [
            "id",
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
    title = StrictStringField()
    description = StrictStringField()

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

    def validate_title(self, value):

        value = value.strip()

        existing_project = Project.objects.filter(
            title__iexact=value
        )

        if self.instance:
            existing_project = existing_project.exclude(
                id=self.instance.id
            )

        if existing_project.exists():
            raise serializers.ValidationError(
                "A project with this title already exists."
            )

        return value
    
    
    def validate_type(self, value):
        from .models import ProjectType

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Project type cannot be empty."
            )

        project_type = ProjectType.objects.filter(
            name__iexact=value
        ).first()

        if project_type:
            if not project_type.is_active:
                raise serializers.ValidationError(
                    "This project type is inactive."
                )

            return project_type.name

        project_type = ProjectType.objects.create(
            name=value,
            is_active=True
        )

        return project_type.name


    def validate_status(self, value):
        from .models import ProjectStatus

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Project status cannot be empty."
            )

        project_status = ProjectStatus.objects.filter(
            name__iexact=value
        ).first()

        if project_status:
            if not project_status.is_active:
                raise serializers.ValidationError(
                    "This project status is inactive."
                )

            return project_status.name

        project_status = ProjectStatus.objects.create(
            name=value,
            is_active=True
        )

        return project_status.name

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

              
