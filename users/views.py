
from django.contrib.auth import get_user_model
from django.utils import timezone

from django.views.generic import ListView
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken


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
        users = User.objects.filter(
            status="Active"
        ).order_by("id")

        paginator = PageNumberPagination()
        paginator.page_size = 2
        page = paginator.paginate_queryset(users, request, view=self)

        serializer = UserSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        # Email failure should not undo a successfully created user.
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
        paginator.page_size = 2
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



# PROJECT LIST AND CREATE
# GET  /api/projects/
# POST /api/projects/
# JWT authentication required

class ProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(
            is_deleted=False
        ).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )




class ProfileListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        profiles = Profile.objects.filter(is_active=True).values(
            "id",
            "name",
            "is_active",
            "is_default"
        )

        return Response(list(profiles))
# PROJECT DETAIL, UPDATE, SOFT DELETE
# GET / PUT / PATCH / DELETE /api/projects/<pk>/

class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(is_deleted=False)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.deleted_by = self.request.user
        instance.deleted_at = timezone.now()
        instance.updated_by = self.request.user
        instance.save(
            update_fields=[
                "is_deleted",
                "deleted_by",
                "deleted_at",
                "updated_by",
                "updated_at",
            ]
        )
