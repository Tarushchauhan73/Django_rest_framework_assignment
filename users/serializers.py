
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Client, Profile, Project

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

    class Meta:
        model = Profile
        fields = ["id", "name", "is_active", "is_default"]


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
    )

    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=False,
        style={"input_type": "password"},
    )

    profiles = serializers.SlugRelatedField(
     slug_field="name",
     queryset=Profile.objects.filter(is_active=True),
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
     profile = validated_data.get("profiles")

     if profile is None:
        profile = Profile.objects.filter(
            name="Standard",
            is_active=True,
            is_default=True,
        ).first()

        if profile is None:
            profile = Profile.objects.filter(
                name="Standard",
                is_active=True,
            ).first()

        if profile is None:
            raise serializers.ValidationError({
                "profiles": "The active Standard profile does not exist."
            })

        validated_data["profiles"] = profile

     password = validated_data.pop("password", None)

     user = User(**validated_data)

     if not password:
        email = user.email or ""
        password = email.split("@")[0] + "@123"

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


class ProjectSerializer(serializers.ModelSerializer):
    client = serializers.SlugRelatedField(
        slug_field="fname",
        queryset=Client.objects.all()
    )

    manager = serializers.SlugRelatedField(
        slug_field="username",
        queryset=User.objects.all()
    )

    class Meta:
        model = Project
        fields = "__all__"
        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "updated_by",
            "updated_at",
            "deleted_by",
            "deleted_at",
        ]
