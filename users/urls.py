
from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenRefreshView



urlpatterns = [
    # User CRUD APIs
    path("users/", views.UserListCreateView.as_view(), name="user-list-create"),
    path("users/<int:pk>/", views.UserDetailView.as_view(), name="user-detail"),

    # Authentication APIs
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    # OTP and password reset APIs
    path("auth/send-otp/", views.SendOTPView.as_view(), name="send-otp"),
    path("auth/verify-otp/", views.VerifyOTPView.as_view(), name="verify-otp"),
    path("auth/forgot-password/", views.ForgotPasswordView.as_view(), name="forgot-password"),
    path("auth/reset-password/", views.ResetPasswordView.as_view(), name="reset-password"),
]
