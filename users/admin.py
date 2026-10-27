
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User, Profile, Client, Project


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "is_active", "is_default"]
    list_filter = ["is_active", "is_default"]
    search_fields = ["name"]


@admin.register(User)
class CustomUserAdmin(DjangoUserAdmin):
    list_display = ["id", "email", "username", "profiles", "status"]
    search_fields = ["email", "username"]
    list_filter = ["status", "profiles"]


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ["id", "fname", "lname", "email", "status"]
    search_fields = ["fname", "lname", "email"]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = [
        "id", "title", "type", "status", "client",
        "manager", "is_deleted",
    ]
    list_filter = ["type", "status", "is_deleted"]
    search_fields = ["title"]
