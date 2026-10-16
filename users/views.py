
from django.contrib.auth import get_user_model

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from .models import OTP
from .serializers import UserSerializer
from .emails_ytils import send_welcome_email, send_otp_email


User = get_user_model()


# 1. Create a user and list active users
class UserListCreateView(generics.ListCreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return User.objects.filter(status="Active")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        try:
            send_welcome_email(user)
        except Exception:
            # User creation succeeds even if email delivery fails.
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


# 3. Login using email and password
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

        user = User.objects.filter(
            email__iexact=email
        ).first()

        if (
            user is None
            or user.status != "Active"
            or not user.check_password(password)
        ):
            return Response(
                {
                    "detail": (
                        "Invalid email or password, "
                        "or inactive account."
                    )
                },
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


# 4. Send email-verification OTP
class SendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip()

        user = User.objects.filter(
            email__iexact=email,
            status="Active",
        ).first()

        if not user:
            return Response(
                {"detail": "Active user not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        otp_record = OTP.generate_otp(
            user,
            OTP.PurposeChoices.EMAIL_VERIFICATION,
        )

        try:
            send_otp_email(user, otp_record.otp)
        except Exception:
            otp_record.delete()
            return Response(
                {"detail": "Unable to send OTP email."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "message": (
                    "OTP sent successfully. "
                    "It expires in 5 minutes."
                )
            },
            status=status.HTTP_200_OK,
        )


# 5. Verify email-verification OTP
class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip()
        entered_otp = request.data.get("otp", "").strip()

        user = User.objects.filter(
            email__iexact=email,
            status="Active",
        ).first()

        if not user or not entered_otp:
            return Response(
                {"detail": "Valid email and OTP are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp_record = OTP.objects.filter(
            user=user,
            purpose=OTP.PurposeChoices.EMAIL_VERIFICATION,
        ).first()

        if (
            not otp_record
            or not otp_record.verify_otp(entered_otp)
        ):
            return Response(
                {"detail": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # The verified record cannot be used again.
        otp_record.delete()

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
            email__iexact=email,
            status="Active",
        ).first()

        # Avoid revealing whether the account exists.
        if user:
            otp_record = OTP.generate_otp(
                user,
                OTP.PurposeChoices.PASSWORD_RESET,
            )

            try:
                send_otp_email(user, otp_record.otp)
            except Exception:
                otp_record.delete()
                return Response(
                    {"detail": "Unable to send reset OTP email."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(
            {
                "message": (
                    "If the account exists, "
                    "a reset OTP has been sent."
                )
            },
            status=status.HTTP_200_OK,
        )


# 7. Reset password using password-reset OTP
class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip()
        entered_otp = request.data.get("otp", "").strip()
        new_password = request.data.get("new_password", "")

        if not email or not entered_otp or not new_password:
            return Response(
                {
                    "detail": (
                        "Email, OTP, and new_password are required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(new_password) < 8:
            return Response(
                {
                    "detail": (
                        "Password must contain at least "
                        "8 characters."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(
            email__iexact=email,
            status="Active",
        ).first()

        if not user:
            return Response(
                {"detail": "Invalid or expired reset OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp_record = OTP.objects.filter(
            user=user,
            purpose=OTP.PurposeChoices.PASSWORD_RESET,
        ).first()

        if (
            not otp_record
            or not otp_record.verify_otp(entered_otp)
        ):
            return Response(
                {"detail": "Invalid or expired reset OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])

        otp_record.delete()

        return Response(
            {"message": "Password reset successfully."},
            status=status.HTTP_200_OK,
        )
