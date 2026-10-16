
import secrets

from django.core.cache import cache
from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import UserSerializer
from .emails_ytils import send_welcome_email, send_otp_email

User = get_user_model()


# 1. Create a user and list active users
class UserListCreateView(generics.ListCreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(status="Active")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        try:
            send_welcome_email(user)
        except Exception:
            # The user is created even if email delivery fails.
            pass

        return Response(
            {
                "message": "User created successfully.",
                "user": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


# 2. Retrieve, update, and soft-delete a user
class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return User.objects.all()

    def perform_destroy(self, instance):
        instance.status = "Inactive"
        instance.save(update_fields=["status"])


# 3. Login using email and password; return JWT tokens
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip()
        password = request.data.get("password", "")

        if not email or not password:
            return Response(
                {"detail": "Email and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email__iexact=email).first()

        if (
            user is None
            or user.status != "Active"
            or not user.check_password(password)
        ):
            return Response(
                {"detail": "Invalid email or password, or inactive account."},
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


# 4. Send an email-verification OTP
class SendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip()

        user = User.objects.filter(
            email__iexact=email, status="Active"
        ).first()

        if not user:
            return Response(
                {"detail": "Active user not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        otp = f"{secrets.randbelow(1_000_000):06d}"
        cache.set(f"email_otp:{user.id}", otp, timeout=300)

        try:
            send_otp_email(user, otp)
        except Exception:
            cache.delete(f"email_otp:{user.id}")
            return Response(
                {"detail": "Unable to send OTP email. Check email configuration."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"message": "OTP sent successfully. It expires in 5 minutes."},
            status=status.HTTP_200_OK,
        )


# 5. Verify the email-verification OTP
class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip()
        otp = request.data.get("otp", "").strip()

        user = User.objects.filter(
            email__iexact=email, status="Active"
        ).first()

        if not user or not otp:
            return Response(
                {"detail": "Valid email and OTP are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        key = f"email_otp:{user.id}"
        saved_otp = cache.get(key)

        if saved_otp is None or saved_otp != otp:
            return Response(
                {"detail": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache.delete(key)

        return Response(
            {"message": "OTP verified successfully."},
            status=status.HTTP_200_OK,
        )


# 6. Request a password-reset OTP
class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip()

        user = User.objects.filter(
            email__iexact=email, status="Active"
        ).first()

        # Do not reveal whether an email is registered.
        if user:
            otp = f"{secrets.randbelow(1_000_000):06d}"
            key = f"password_reset_otp:{user.id}"
            cache.set(key, otp, timeout=300)

            try:
                send_otp_email(user, otp)
            except Exception:
                cache.delete(key)
                return Response(
                    {"detail": "Unable to send reset OTP email."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(
            {"message": "If the account exists, a reset OTP has been sent."},
            status=status.HTTP_200_OK,
        )


# 7. Reset password using the password-reset OTP
class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip()
        otp = request.data.get("otp", "").strip()
        new_password = request.data.get("new_password", "")

        if not email or not otp or not new_password:
            return Response(
                {"detail": "Email, OTP, and new_password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(new_password) < 8:
            return Response(
                {"detail": "Password must contain at least 8 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(
            email__iexact=email, status="Active"
        ).first()

        if not user:
            return Response(
                {"detail": "Invalid or expired reset OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        key = f"password_reset_otp:{user.id}"
        saved_otp = cache.get(key)

        if saved_otp is None or saved_otp != otp:
            return Response(
                {"detail": "Invalid or expired reset OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])
        cache.delete(key)

        return Response(
            {"message": "Password reset successfully."},
            status=status.HTTP_200_OK,
        )
