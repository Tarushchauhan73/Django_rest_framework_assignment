
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Client

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
        required_fields = ["fname", "lname", "email"]

        for field in required_fields:
            value = attrs.get(field)

            # During updates, existing values can remain unchanged.
            if self.instance is not None and field not in attrs:
                continue

            if value is None or (
                isinstance(value, str) and not value.strip()
            ):
                raise serializers.ValidationError({
                    field: f"{field.capitalize()} is required."
                })

        return attrs


class UserSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=False,
        style={"input_type": "password"},
)

    username = serializers.CharField(
        required=True,
        allow_blank=False,
    )

    email = serializers.EmailField(
        required=True,
        allow_blank=False,
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
            "profile",
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

    def validate(self, attrs):
        # Require these fields when creating a user.
        if self.instance is None:
            required_fields = ["username", "email", "password"]

            for field in required_fields:
                value = attrs.get(field)

                if value is None or (
                    isinstance(value, str) and not value.strip()
                ):
                    raise serializers.ValidationError({
                        field: f"{field.replace('_', ' ').capitalize()} is required."
                    })

        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)

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
        if not User.objects.filter(
            email__iexact=value,
            status="Active",
        ).exists():
            raise serializers.ValidationError(
                "No active user found with this email."
            )

        return value
