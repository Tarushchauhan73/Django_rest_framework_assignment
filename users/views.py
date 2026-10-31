
from django.contrib.auth import get_user_model
from django.http import request
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser

from django.utils import timezone

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

        users = users.order_by("id")

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

    def patch(self, request, pk):
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
        clients = Client.objects.all().order_by("id")

        paginator = PageNumberPagination()
        paginator.page_size = 100
        page = paginator.paginate_queryset(
            clients, request, view=self
        )

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

    def delete(self, request, pk):
        client = self.get_object(pk)

        if client is None:
            return Response(
                {"error": "Client not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        client.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

class ClientRestoreView(APIView):
    permission_classes = [AllowAny]

    def patch(self, request, pk):
        client = Client.objects.filter(pk=pk).first()

        if not client:
            return Response(
                {"error": "Client not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if client.status == "Active":
            return Response(
                {"message": "Client is already active."},
                status=status.HTTP_200_OK
            )

        client.status = "Active"
        client.save(update_fields=["status"])

        return Response(
            {
                "message": "Client restored successfully.",
                "client": ClientSerializer(client).data
            },
            status=status.HTTP_200_OK
        )

# PROJECT LIST AND CREATE
# GET  /api/projects/
# POST /api/projects/
# JWT authentication required

class ProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return Project.objects.filter(
            is_deleted=False
        ).order_by("created_at")

    def perform_create(self, serializer):
     print("CONTENT TYPE:", self.request.content_type)
     print("FILES:", self.request.FILES)
     print("FILE KEYS:", list(self.request.FILES.keys()))
     print(
        "ATTACHMENTS:",
        self.request.FILES.getlist("attachments")
    )

     serializer.save(
        created_by=self.request.user,
        updated_by=self.request.user,
    )

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

        # Do not assign AnonymousUser to updated_by.
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
        "Administrator",
        "Standard",
        "Developer",
        "Client",
        "Human Resource",
    ]

    def get(self, request):
        profiles = Profile.objects.filter(
            is_active=True
        ).order_by("id")

        serializer = ProfileSerializer(profiles, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name = serializer.validated_data["name"]

        is_default = name.casefold() in [
            profile.casefold()
            for profile in self.DEFAULT_PROFILES
        ]

        profile = serializer.save(is_default=is_default)

        return Response(
            ProfileSerializer(profile).data,
            status=status.HTTP_201_CREATED,
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
     project = self.get_object(pk)

     attachment_id = request.data.get("attachment_id")

     # CASE 1: Hard delete a specific attachment
     if attachment_id:
        try:
            attachment = project.attachments.get(id=attachment_id)
        except ProjectAttachement.DoesNotExist:
            raise NotFound("Attachment not found in this project.")

        attachment.file.delete(save=False)
        attachment.delete()

        return Response(
            {"message": f"Attachment {attachment_id} permanently deleted."},
            status=status.HTTP_200_OK
        )

    # CASE 2: Soft delete the entire project
     project.is_deleted = True
     project.deleted_at = timezone.now()
     project.deleted_by = request.user
     project.save(
        update_fields=["is_deleted", "deleted_at", "deleted_by"]
    )

     return Response(
        {"message": f"Project {pk} soft deleted successfully."},
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
    parser_classes = [MultiPartParser, FormParser]

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