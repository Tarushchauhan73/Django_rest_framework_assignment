
import profile
from typing import Self

from django.contrib.auth import get_user_model
from django.db.migrations import serializer
from django.http import request
from django.test import client
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
import json
from django.utils import  timezone
from django.db.models import Q
from django.views.generic import ListView
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import NotFound
from django.shortcuts import get_object_or_404
from rest_framework import status

from rest_framework.response import Response
from rest_framework.views import APIView
from .utils import send_project_notifications
from .models import Project, ProjectAttachement
from .serializers import ProjectAttachementSerializer
from .models import Client, Project, Profile
from .serializers import (
    UserSerializer,
    ClientSerializer,
    ProjectSerializer,
    SendOTPSerializer,
    ProfileSerializer,
)
from .emails_ytils import send_welcome_email, send_otp_email
from .utils import (
    generate_otp,
    verify_otp,
    clear_otp,
    check_otp_request_limit,
)
from .utils import send_project_notifications

User = get_user_model()



# USER LIST AND CREATE
# GET  /api/users/
# POST /api/users/
class UserListCreateView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        users = User.objects.filter(status="Active")

        # Filter users by profile ID
        profile_id = request.query_params.get("profile_id")

        if profile_id:
            users = users.filter(profiles_id=profile_id)

        # Filter users by role/profile name
        role = request.query_params.get("role")

        if role:
            users = users.filter(
                profiles__name__iexact=role.strip()
            )

        first_name = request.query_params.get("first_name")
        last_name = request.query_params.get("last_name")
        email = request.query_params.get("email")
        phone = request.query_params.get("phone")
        nationality = request.query_params.get("nationality")
        gender = request.query_params.get("gender")

        if first_name:
            users = users.filter(first_name__icontains=first_name)

        if last_name:
            users = users.filter(last_name__icontains=last_name)

        if email:
            users = users.filter(email__icontains=email)

        if phone:
            users = users.filter(phone__icontains=phone)

        if nationality:
            users = users.filter(nationality__icontains=nationality)

        if gender:
            users = users.filter(gender__iexact=gender)

        # General search across multiple fields
        search = request.query_params.get("search")

        if search:
            users = users.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search) |
                Q(nationality__icontains=search) |
                Q(profiles__name__icontains=search)
            )

        # Remove duplicate records and order users
        users = users.order_by("id").distinct()

        paginator = PageNumberPagination()
        paginator.page_size = 100

        page = paginator.paginate_queryset(
            users, request, view=self
        )

        serializer = UserSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        try:
            send_welcome_email(user)
        except Exception:
            pass

        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )



# USER DETAIL, UPDATE AND SOFT DELETE
# GET    /api/users/<pk>/
# PUT    /api/users/<pk>/
# PATCH  /api/users/<pk>/
# DELETE /api/users/<pk>/

class UserDetailView(APIView):
    permission_classes = [AllowAny]

    def get_object(self, pk):
        return User.objects.filter(
            pk=pk,
            status="Active",
        ).first()

    def get(self, request, pk):
        user = self.get_object(pk)

        if user is None:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(UserSerializer(user).data)

    def put(self, request, pk):
        return self.update_user(request, pk, partial=False)

    def patch(self, request, pk):
        return self.update_user(request, pk, partial=True)

    def update_user(self, request, pk, partial):
        user = self.get_object(pk)

        if user is None:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = UserSerializer(
            user,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        user = self.get_object(pk)

        if user is None:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user.status = "Inactive"
        user.save(update_fields=["status"])

        return Response(
            {"message": "User deleted successfully."},
            status=status.HTTP_200_OK,
        )

class UserRestoreView(APIView):
    permission_classes = [AllowAny]

    def patch(self, request, pk=None):
        # Bulk restore
        if pk is None:
            user_ids = request.data.get("user_ids")

            if not isinstance(user_ids, list) or not user_ids:
                return Response(
                    {"error": "Please provide a non-empty user_ids list."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            users = User.objects.filter(
                pk__in=user_ids,
                status="Inactive"
            )

            restored_users = []

            for user in users:
                user.status = "Active"
                user.save(update_fields=["status"])
                restored_users.append(user)

            return Response(
                {
                    "message": "Users restored successfully.",
                    "restored_count": len(restored_users),
                    "users": UserSerializer(
                        restored_users, many=True
                    ).data
                },
                status=status.HTTP_200_OK
            )

        # Single restore
        user = User.objects.filter(pk=pk).first()

        if not user:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if user.status == "Active":
            return Response(
                {"message": "User is already active."},
                status=status.HTTP_200_OK
            )

        user.status = "Active"
        user.save(update_fields=["status"])

        return Response(
            {
                "message": "User restored successfully.",
                "user": UserSerializer(user).data
            },
            status=status.HTTP_200_OK
        )

  # LOGIN
  # POST /api/login/

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"error": "Email and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(
            email__iexact=email.strip(),
            status="Active",
        ).first()

        if user is None or not user.check_password(password):
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Login successful.",
                "user_id": user.id,
                "email": user.email,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )



 # SEND EMAIL VERIFICATION OTP
 # POST /api/send-otp/

class SendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        user = User.objects.filter(
            email__iexact=email,
            status="Active",
        ).first()

        if user is None:
            raise ValidationError(
                {"email": "Active user not found."}
            )

        # Shared limit: maximum 3 OTP sends per 12-hour window.
        check_otp_request_limit(user)

        otp = generate_otp(
            user,
            User.OTPPurposeChoices.EMAIL_VERIFICATION,
        )
        send_otp_email(user, otp)

        return Response(
            {"message": "Verification OTP sent to your email."},
            status=status.HTTP_200_OK,
        )



 # VERIFY EMAIL OTP
 # POST /api/verify-otp/

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        entered_otp = request.data.get("otp")

        if not email or not entered_otp:
            return Response(
                {"error": "Email and OTP are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(
            email__iexact=email.strip(),
            status="Active",
        ).first()

        if user is None:
            return Response(
                {"error": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid = verify_otp(
            user,
            entered_otp,
            User.OTPPurposeChoices.EMAIL_VERIFICATION,
        )

        if not valid:
            return Response(
                {"error": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        clear_otp(user)

        return Response(
            {"message": "Email OTP verified successfully."},
            status=status.HTTP_200_OK,
        )



 # FORGOT PASSWORD: SEND OTP
 # POST /api/forgot-password/

class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response(
                {"error": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(
            email__iexact=email.strip(),
            status="Active",
        ).first()

         # Do not reveal whether the email exists.
        if user is not None:
            check_otp_request_limit(user)

            otp = generate_otp(
                user,
                User.OTPPurposeChoices.PASSWORD_RESET,
            )
            send_otp_email(user, otp)

        return Response(
            {
                "message": (
                    "If an active account exists, "
                    "a password reset OTP has been sent."
                )
            },
            status=status.HTTP_200_OK,
        )



 # RESET PASSWORD
 # POST /api/reset-password/

class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        entered_otp = request.data.get("otp")
        new_password = request.data.get("new_password")

        if not email or not entered_otp or not new_password:
            return Response(
                {
                    "error": (
                        "Email, OTP, and new_password are required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(new_password) < 8:
            return Response(
                {
                    "error": (
                        "Password must be at least 8 characters long."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(
            email__iexact=email.strip(),
            status="Active",
        ).first()

        if user is None:
            return Response(
                {"error": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid = verify_otp(
            user,
            entered_otp,
            User.OTPPurposeChoices.PASSWORD_RESET,
        )

        if not valid:
            return Response(
                {"error": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])
        clear_otp(user)

        return Response(
            {"message": "Password reset successfully."},
            status=status.HTTP_200_OK,
        )



# CLIENT LIST AND CREATE
# GET  /api/clients/
# POST /api/clients/
# JWT authentication required

class ClientListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        clients = Client.objects.all()

        fname = request.query_params.get("fname")
        lname = request.query_params.get("lname")
        email = request.query_params.get("email")
        contactno = request.query_params.get("contactno")
        country = request.query_params.get("country")
        address = request.query_params.get("address")
        client_status = request.query_params.get("status")

        if fname:
            clients = clients.filter(fname__icontains=fname)

        if lname:
            clients = clients.filter(lname__icontains=lname)

        if email:
            clients = clients.filter(email__icontains=email)

        if contactno:
            clients = clients.filter(contactno__icontains=contactno)

        if country:
            clients = clients.filter(country__icontains=country)

        if address:
            clients = clients.filter(address__icontains=address)

        if client_status:
            clients = clients.filter(status__iexact=client_status)

        # General search across multiple fields
        search = request.query_params.get("search")

        if search:
            clients = clients.filter(
                  Q(fname__icontains=search)
                 | Q(lname__icontains=search)
                | Q(email__icontains=search)
                | Q(contactno__icontains=search)
                | Q(country__icontains=search)
                | Q(address__icontains=search)
            )

        # Remove duplicates and order results
        clients = clients.order_by("id").distinct()

        paginator = PageNumberPagination()
        paginator.page_size = 100
        page = paginator.paginate_queryset(clients, request, view=self)

        serializer = ClientSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ClientSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save(
            created_by=request.user,
            updated_by=request.user,
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )


# CLIENT DETAIL, UPDATE AND DELETE
# GET / PUT / PATCH / DELETE /api/clients/<pk>/
# JWT authentication required

class ClientDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return Client.objects.filter(pk=pk).first()

    def get(self, request, pk):
        client = self.get_object(pk)

        if client is None:
            return Response(
                {"error": "Client not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(ClientSerializer(client).data)

    def put(self, request, pk):
        return self.update_client(request, pk, partial=False)

    def patch(self, request, pk):
        return self.update_client(request, pk, partial=True)

    def update_client(self, request, pk, partial):
        client = self.get_object(pk)

        if client is None:
            return Response(
                {"error": "Client not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ClientSerializer(
            client,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)

        return Response(serializer.data)

class ClientDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        client = Client.objects.filter(
            pk=pk,
            status="Active"
        ).first()

        if client is None:
            return Response(
                {"error": "Client not found or already inactive."},
                status=status.HTTP_404_NOT_FOUND
            )

        client.status = "Inactive"
        client.updated_by = request.user
        client.save()

        return Response(
            {"message": "Client soft-deleted successfully."},
            status=status.HTTP_200_OK
        )

class ClientRestoreView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk=None):
        # Bulk restore
        if pk is None:
            client_ids = request.data.get("client_ids")

            if not isinstance(client_ids, list) or not client_ids:
                return Response(
                    {"error": "Please provide a non-empty client_ids list."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            clients = Client.objects.filter(
                pk__in=client_ids,
                status="Inactive"
            )

            restored_clients = []

            for client in clients:
                client.status = "Active"
                client.updated_by = request.user
                client.save()
                restored_clients.append(client)

            return Response(
                {
                    "message": "Clients restored successfully.",
                    "restored_count": len(restored_clients),
                    "clients": ClientSerializer(
                        restored_clients, many=True
                    ).data
                },
                status=status.HTTP_200_OK
            )

        # Single restore
        client = Client.objects.filter(
            pk=pk,
            status="Inactive"
        ).first()

        if client is None:
            return Response(
                {"error": "Client not found or already active."},
                status=status.HTTP_404_NOT_FOUND
            )

        client.status = "Active"
        client.updated_by = request.user
        client.save()

        return Response(
            {
                "message": "Client restored successfully.",
                "client": ClientSerializer(client).data
            },
            status=status.HTTP_200_OK
        )
# PROJECT LIST AND CREATE


class ProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return Project.objects.none()

        profile = getattr(user, "profiles", None)

        if profile is None:
            return Project.objects.none()

        role = profile.name.strip().lower()

        projects = Project.objects.filter(is_deleted=False)

        if role in ["superadmin", "admin"]:
            pass
        elif role == "manager":
            projects = projects.filter(manager=user)
        else:
            return Project.objects.none()

        search = self.request.query_params.get("search", "").strip()

        if search:
            projects = projects.filter(
                Q(title__icontains=search) |
                Q(manager__username__icontains=search) |
                Q(manager__first_name__icontains=search) |
                Q(manager__last_name__icontains=search) |
                Q(manager__email__icontains=search) |
                Q(client__fname__icontains=search) |
                Q(client__lname__icontains=search) |
                Q(client__email__icontains=search) |
                Q(type__icontains=search)
            )

        role = self.request.query_params.get("role", "").strip()
        if role:
            projects = projects.filter(
                manager__profiles__name__iexact=role
            )

        return projects.order_by("created_at").distinct()

    def perform_create(self, serializer):
        project = serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )

        try:
            self.notification_results = send_project_notifications(project)
        except Exception:
            import logging
            logging.exception("Project notification email failed.")

            self.notification_results = {
                "client": {"status": "failed"},
                "manager": {"status": "failed"},
            }

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)

        if response.status_code == 201:
            response.data["email_notifications"] = getattr(
                self,
                "notification_results",
                {},
            )

        return response
    

class ProjectRestoreView(APIView):
    parser_classes = [AllowAny]
    authentication_classes = [] 
    permission_classes = [AllowAny]

    def patch(self, request, pk):
        project = Project.objects.filter(pk=pk).first()

        if not project:
            return Response(
                {"error": "Project not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if not project.is_deleted:
            return Response(
                {"message": "Project is already active."},
                status=status.HTTP_200_OK
            )

        project.is_deleted = False
        project.deleted_at = None
        project.deleted_by = None
        project.updated_by = request.user
        project.save()

        return Response(
            {
                "message": "Project restored successfully.",
                "project": ProjectSerializer(
                    project,
                    context={"request": request}
                ).data
            },
            status=status.HTTP_200_OK
        )
class ProjectRestoreView(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    authentication_classes = []
    permission_classes = [AllowAny]

    def patch(self, request, pk=None):
        # Bulk restore
        if pk is None:
            project_ids = request.data.get("project_ids")

            if not isinstance(project_ids, list) or not project_ids:
                return Response(
                    {"error": "Please provide a non-empty project_ids list."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            projects = Project.objects.filter(
                pk__in=project_ids,
                is_deleted=True
            )

            restored_projects = []

            for project in projects:
                project.is_deleted = False
                project.deleted_at = None
                project.deleted_by = None

                project.save(
                    update_fields=[
                        "is_deleted",
                        "deleted_at",
                        "deleted_by"
                    ]
                )

                restored_projects.append(project)

            return Response(
                {
                    "message": "Projects restored successfully.",
                    "restored_count": len(restored_projects),
                    "projects": ProjectSerializer(
                        restored_projects,
                        many=True,
                        context={"request": request}
                    ).data
                },
                status=status.HTTP_200_OK
            )

        # Single restore
        project = Project.objects.filter(pk=pk).first()

        if not project:
            return Response(
                {"error": "Project not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if not project.is_deleted:
            return Response(
                {"message": "Project is already active."},
                status=status.HTTP_200_OK
            )

        project.is_deleted = False
        project.deleted_at = None
        project.deleted_by = None

        project.save(
            update_fields=[
                "is_deleted",
                "deleted_at",
                "deleted_by"
            ]
        )

        return Response(
            {
                "message": "Project restored successfully.",
                "project": ProjectSerializer(
                    project,
                    context={"request": request}
                ).data
            },
            status=status.HTTP_200_OK
        )
    
class ProfileListView(APIView):
    permission_classes = [AllowAny]

    DEFAULT_PROFILES = [
        "superadmin",
        "admin",
        "manager",
        "teamleader",
        "developer",
        "HR"
    ]

    def get(self, request):
        profiles = Profile.objects.filter(
            is_active=True
        ).order_by("id")

        serializer = ProfileSerializer(profiles, many=True)
        return Response(serializer.data)

    def post(self, request):
     role = request.data.get("role")

     if not role or not isinstance(role, str):
        return Response(
            {"error": "Role is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

     role = role.strip()

   
     if Profile.objects.filter(name__iexact=role).exists():
        return Response(
            {"error": "This profile already exists."},
            status=status.HTTP_400_BAD_REQUEST
        )

     serializer = ProfileSerializer(
        data={"role": role}
    )

     serializer.is_valid(raise_exception=True)

   
     is_default = role.casefold() in {
        name.casefold() for name in self.DEFAULT_PROFILES
    }

     profile = serializer.save(
        is_default=is_default,
        is_active=True
    )

     return Response(
        ProfileSerializer(profile).data,
        status=status.HTTP_201_CREATED
    )
class ProfileDetailView(APIView):
    permission_classes = [AllowAny]

    def get_object(self, pk):
        try:
            return Profile.objects.get(pk=pk)
        except Profile.DoesNotExist:
            return None

    def get(self, request, pk):
        profile = self.get_object(pk)

        if profile is None:
            return Response(
                {"error": "Role not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(ProfileSerializer(profile).data)

    def put(self, request, pk):
        return self.update_role(request, pk, partial=False)

    def patch(self, request, pk):
        return self.update_role(request, pk, partial=True)

    def update_role(self, request, pk, partial=False):
        profile = self.get_object(pk)

        if profile is None:
            return Response(
                {"error": "Role not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if profile.is_default:
            return Response(
                {"error": "Default roles cannot be updated."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ProfileSerializer(
            profile,
            data=request.data,
            partial=partial,
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    def delete(self, request, pk):
        profile = self.get_object(pk)

        if profile is None:
            return Response(
                {"error": "Role not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if profile.is_default:
            return Response(
                {"error": "Default roles cannot be deleted."},
                status=status.HTTP_403_FORBIDDEN,
            )

        profile.delete()

        return Response(
            {"message": "Role deleted successfully."},
            status=status.HTTP_200_OK,
        )

 # PROJECT DETAIL, UPDATE, SOFT DELETE


class ProjectDetailView(APIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(is_deleted=False)

    def get_object(self, pk):
        project = self.get_queryset().filter(pk=pk).first()

        if project is None:
            raise NotFound("Project not found.")

        return project

    def get(self, request, pk):
        project = self.get_object(pk)
        serializer = self.serializer_class(project)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        project = self.get_object(pk)

        serializer = self.serializer_class(
            project,
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        project = self.get_object(pk)

        serializer = self.serializer_class(
            project,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)

        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def delete(self, request, pk):
     project = Project.objects.filter(pk=pk).first()

     if not project:
        return Response(
            {"error": "Project not found."},
            status=status.HTTP_404_NOT_FOUND
        )

     attachment_ids = request.data.get("attachment_ids")
     delete_all = request.data.get("delete_all_attachments", False)


    # Convert form-data string into a Boolean
     if isinstance(delete_all, str):
        delete_all = delete_all.lower() in ["true", "1", "yes"]

   
     if delete_all:
        attachments = project.attachments.all()

     elif attachment_ids is not None:

      
        if isinstance(attachment_ids, str):
            try:
                attachment_ids = json.loads(attachment_ids)
            except json.JSONDecodeError:
                return Response(
                    {"error": "Invalid attachment IDs format."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if not isinstance(attachment_ids, list) or not attachment_ids:
            return Response(
                {"error": "Provide a non-empty list of attachment IDs."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            attachment_ids = list(set(int(i) for i in attachment_ids))
        except (ValueError, TypeError):
            return Response(
                {"error": "All attachment IDs must be integers."},
                status=status.HTTP_400_BAD_REQUEST
            )

        attachments = project.attachments.filter(
            id__in=attachment_ids
        )

        if attachments.count() != len(attachment_ids):
            return Response(
                {
                    "error": "One or more attachments were not found in this project."
                },
                status=status.HTTP_404_NOT_FOUND
            )

     else:
        # Soft-delete the entire project
        project.is_deleted = True
        project.deleted_at = timezone.now()
        project.deleted_by = request.user
        project.save()

        return Response(
            {
                "message": f"Project {project.id} soft deleted successfully."
            },
            status=status.HTTP_200_OK
        )

    # Delete physical files and database records
     deleted_count = attachments.count()

     for attachment in attachments:
        if attachment.file:
            attachment.file.delete(save=False)

     attachments.delete()

     return Response(
        {
            "message": "Attachments deleted successfully.",
            "deleted_count": deleted_count
        },
        status=status.HTTP_200_OK
    )
class ProjectAttachementDetailView(APIView):
     permission_classes = [IsAuthenticated]

     def delete(self, request, project_id, attachement_id):
        attachment = ProjectAttachement.objects.filter(
            pk=attachement_id,
            project_id=project_id,
        ).first()

        if attachment is None:
            return Response(
                {"error": "Attachment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Keep a reference to the physical file
        stored_file = attachment.file

        # Delete the attachment record
        attachment.delete()

        # Delete the actual uploaded file
        if stored_file:
            stored_file.delete(save=False)

        return Response(
            {"message": "Attachment permanently deleted."},
            status=status.HTTP_200_OK,
        )

class ProjectAttachementListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request, project_id):
        project = get_object_or_404(
            Project,
            pk=project_id,
            is_deleted=False,
        )
        attachments = project.attachments.all()
        serializer = ProjectAttachementSerializer(
            attachments,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)

    def post(self, request, project_id):
        project = Project.objects.filter(pk=project_id).first()

        if project is None:
            return Response(
                {"error": "Project not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ProjectAttachementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attachment = serializer.save(project=project)

        return Response(
            ProjectAttachementSerializer(attachment).data,
            status=status.HTTP_201_CREATED,
        )


class ProjectAttachementDetailView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, project_id, attachement_id):
        attachment = get_object_or_404(
            ProjectAttachement,
            pk=attachement_id,
            project_id=project_id,
            project__is_deleted=False,
        )

        serializer = ProjectAttachementSerializer(
            attachment,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    class ProjectAttachementDetailView(APIView):
     permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
     project = self.get_object(pk)

     attachment_id = request.data.get("attachment_id")

     if not attachment_id:
        raise ValidationError({
            "attachment_id": "This field is required."
        })

     try:
        attachment = project.attachments.get(id=attachment_id)
     except ProjectAttachement.DoesNotExist:
        raise NotFound("Attachment not found in this project.")

     attachment.file.delete(save=False)
     attachment.delete()

     return Response(
        {"message": "Attachment deleted successfully."},
        status=status.HTTP_200_OK
    )

