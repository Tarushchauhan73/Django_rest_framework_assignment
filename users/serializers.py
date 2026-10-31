
from xml.dom.minidom import Attr

from django.db.models import Value
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Client, Profile, Project, ProjectAttachement 
from .models import Project, ProjectAttachement, Client, User
User = get_user_model()


class ClientSerializer(serializers.ModelSerializer):

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


class ProfileSerializer(serializers.ModelSerializer):
        
    role = serializers.CharField(
        source="name",
        required=True
    )

    class Meta:
        model = Profile
        fields = ["id", "role", "is_active", "is_default"]
        read_only_fields = ["id", "is_default"]

    def validate_name(self, value):
        value = value.strip()

        existing = Profile.objects.filter(name__iexact=value)

        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)

        if existing.exists():
            raise serializers.ValidationError(
                "A profile with this name already exists."
            )

        return value


class UserSerializer(serializers.ModelSerializer):

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

    profiles = ProfileSerializer(read_only=True)

    profile_id = serializers.PrimaryKeyRelatedField(
        queryset=Profile.objects.filter(is_active=True),
        source="profiles",
        write_only=True,
        required=False,
        allow_null=True,
    )

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

    def validate_email(self, value):
        value = value.strip().lower()

        existing = User.objects.filter(email__iexact=value)

        if self.instance is not None:
            existing = existing.exclude(pk=self.instance.pk)

        if existing.exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )

        return value

    
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
        fields = ["id", "username", "first_name", "last_name", "email"]

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
        }



class ProjectAttachementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectAttachement
        fields = [
            "id",
            "file",
            "uploaded_by",
            "uploaded_at",
        ]


class ProjectSerializer(serializers.ModelSerializer):

    client = ClientRelatedField(
        queryset=Client.objects.all(),
        required=False,
        allow_null=True,
    )

    manager = ManagerRelatedField(
        queryset=User.objects.all(),
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
            many=True
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
    

              
