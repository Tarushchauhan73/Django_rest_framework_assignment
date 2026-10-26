

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import ValidationError
from .models import Client
from .serializers import UserSerializer, ClientSerializer
from .emails_ytils import send_welcome_email, send_otp_email
from .serializers import SendOTPSerializer
from .utils import generate_otp, verify_otp, clear_otp
User = get_user_model()







# USER LIST AND CREATE
# GET  /api/users/
# POST /api/users/


class UserListCreateView(APIView):
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def get(self, request):
        users = User.objects.filter(
            status="Active"
        ).order_by("id")

        paginator = PageNumberPagination()
        paginator.page_size = 2

        page = paginator.paginate_queryset(
            users, request, view=self
        )

        serializer = self.serializer_class(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        send_welcome_email(user)

        return Response(
            self.serializer_class(user).data,
            status=status.HTTP_201_CREATED
        )


# USER DETAIL, UPDATE AND SOFT DELETE
# GET    /api/users/<pk>/
# PUT    /api/users/<pk>/
# PATCH  /api/users/<pk>/
# DELETE /api/users/<pk>/


class UserDetailView(APIView):
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def get(self, request, pk):
        user = User.objects.filter(id=pk, status="Active").first()
        if not user:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.serializer_class(user)
        return Response(serializer.data)

    def put(self, request, pk):
        user = User.objects.filter(id=pk, status="Active").first()
        if not user:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.serializer_class(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        user = User.objects.filter(id=pk, status="Active").first()
        if not user:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        user.status = "Inactive"
        user.save(update_fields=["status"])
        return Response({"message": "User deleted successfully."})

    def perform_destroy(self, instance):
        # Soft delete: the database record is retained.
        instance.status = "Inactive"
        instance.save(update_fields=["status"])


# LOGIN USING EMAIL AND PASSWORD
# POST /api/login/


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"error": "Email and password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(
            email__iexact=email,
            status="Active"
        ).first()

        if user is None or not user.check_password(password):
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "Login successful.",
            "user_id": user.id,
            "email": user.email,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }, status=status.HTTP_200_OK)



# SEND EMAIL VERIFICATION OTP
# POST /api/send-otp/
# Body: {"email": "user@example.com"}


class SendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response(
                {"error": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(
            email__iexact=email,
            status="Active"
        ).first()

        if user is None:
            return Response(
                {"error": "Active user not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        otp = generate_otp(
            user,
            User.OTPPurposeChoices.EMAIL_VERIFICATION
        )

        send_otp_email(user, otp)

        return Response(
            {"message": "Verification OTP sent to your email."},
            status=status.HTTP_200_OK
        )



# VERIFY EMAIL OTP
# POST /api/verify-otp/
# Body: {"email": "...", "otp": "123456"}


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        entered_otp = request.data.get("otp")

        if not email or not entered_otp:
            return Response(
                {"error": "Email and OTP are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(
            email__iexact=email,
            status="Active"
        ).first()

        if user is None:
            return Response(
                {"error": "Active user not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        valid = verify_otp(
            user,
            entered_otp,
            User.OTPPurposeChoices.EMAIL_VERIFICATION
        )

        if not valid:
            return Response(
                {"error": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST
            )

        clear_otp(user)

        # Mark email as verified if your model uses this field.
        # This implementation does not add an email_verified field.

        return Response(
            {"message": "Email OTP verified successfully."},
            status=status.HTTP_200_OK
        )



# FORGOT PASSWORD: SEND OTP
# POST /api/forgot-password/
# Body: {"email": "..."}


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response(
                {"error": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(
            email__iexact=email,
            status="Active"
        ).first()

        # Avoid revealing whether an email is registered.
        if user is not None:
            otp = generate_otp(
                user,
                User.OTPPurposeChoices.PASSWORD_RESET
            )
            send_otp_email(user, otp)

        return Response(
            {
                "message":
                "If an active account exists, a password reset OTP has been sent."
            },
            status=status.HTTP_200_OK
        )



# RESET PASSWORD USING OTP
# POST /api/reset-password/
# Body: {
#   "email": "...",
#   "otp": "123456",
#   "new_password": "NewStrongPassword123!"
# }


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        entered_otp = request.data.get("otp")
        new_password = request.data.get("new_password")

        if not email or not entered_otp or not new_password:
            return Response(
                {
                    "error":
                    "Email, OTP, and new_password are required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 8:
            return Response(
                {"error": "Password must be at least 8 characters long."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(
            email__iexact=email,
            status="Active"
        ).first()

        if user is None:
            return Response(
                {"error": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST
            )

        valid = verify_otp(
            user,
            entered_otp,
            User.OTPPurposeChoices.PASSWORD_RESET
        )

        if not valid:
            return Response(
                {"error": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # set_password hashes the password correctly.
        user.set_password(new_password)
        user.save(update_fields=["password"])

        clear_otp(user)

        return Response(
            {"message": "Password reset successfully."},
            status=status.HTTP_200_OK
        )



# CLIENT LIST AND CREATE WITH PAGINATION
# GET  /api/clients/
# POST /api/clients/
# Requires JWT Bearer token


class ClientListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        clients = Client.objects.all().order_by("id")

        paginator = PageNumberPagination()
        paginator.page_size = 2

        page = paginator.paginate_queryset(clients, request, view=self)

        serializer = ClientSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ClientSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(
                created_by=request.user,
                updated_by=request.user
            )

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )



# CLIENT DETAIL, UPDATE AND DELETE
# GET    /api/clients/<pk>/
# PUT    /api/clients/<pk>/
# PATCH  /api/clients/<pk>/
# DELETE /api/clients/<pk>/
# Requires JWT Bearer token


class ClientDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Client.objects.get(pk=pk)
        except Client.DoesNotExist:
            return None

    def get(self, request, pk):
        client = self.get_object(pk)

        if client is None:
            return Response(
                {"error": "Client not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ClientSerializer(client)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        return self.update_client(request, pk, partial=False)

    def patch(self, request, pk):
        return self.update_client(request, pk, partial=True)

    def update_client(self, request, pk, partial):
        client = self.get_object(pk)

        if client is None:
            return Response(
                {"error": "Client not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ClientSerializer(
            client,
            data=request.data,
            partial=partial
        )

        if serializer.is_valid():
            serializer.save(updated_by=request.user)

            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        client = self.get_object(pk)

        if client is None:
            return Response(
                {"error": "Client not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        client.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
    
class SendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        user = User.objects.filter(
            email__iexact=email,
            status="Active"
        ).first()

        if user is None:
            raise ValidationError({
                "email": "Active user not found."
            })

        now = timezone.now()

        # Check if the user is still blocked
        if user.blocked_until and now < user.blocked_until:
            raise ValidationError(
                "You have exceeded the maximum number of OTP requests. "
                "Please try again after 12 hours."
            )

        # Reset the counter after the 12-hour window expires
        if (
            user.otp_window_started_at is None
            or now >= user.otp_window_started_at + timedelta(hours=12)
            or (
                user.blocked_until is not None
                and now >= user.blocked_until
            )
        ):
            user.attempt = 0
            user.otp_window_started_at = now
            user.blocked_until = None

        # If three requests have already been made, block for 12 hours
        if user.attempt >= 3:
            user.blocked_until = now + timedelta(hours=12)
            user.save(update_fields=["blocked_until"])

            raise ValidationError(
                "You have exceeded the maximum number of OTP requests. "
                "Please try again after 12 hours."
            )

        # Count the request
        user.attempt += 1
        user.save(update_fields=[
            "attempt",
            "otp_window_started_at",
            "blocked_until",
        ])

        # Generate and email the OTP
        otp = generate_otp(
            user,
            User.OTPPurposeChoices.EMAIL_VERIFICATION
        )
        send_otp_email(user, otp)

        return Response(
            {"message": "Verification OTP sent to your email."},
            status=status.HTTP_200_OK
        )