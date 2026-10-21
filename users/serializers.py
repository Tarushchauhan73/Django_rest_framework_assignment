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


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"}
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
            "profile",  # Fixed: profile, not profiles
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
