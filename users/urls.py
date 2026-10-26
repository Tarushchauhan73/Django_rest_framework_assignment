
from django.urls import path
from . import views

urlpatterns = [
    # User APIs
    path("users/", views.UserListCreateView.as_view(), name="user-list-create"),
    path("users/<int:pk>/", views.UserDetailView.as_view(), name="user-detail"),

    # Authentication and OTP APIs
    path("login/", views.LoginView.as_view(), name="login"),
    path("send-otp/", views.SendOTPView.as_view(), name="send-otp"),
    path("verify-otp/", views.VerifyOTPView.as_view(), name="verify-otp"),
    path("forgot-password/", views.ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password/", views.ResetPasswordView.as_view(), name="reset-password"),

    # Client APIs
    path("clients/", views.ClientListCreateAPIView.as_view(), name="client-list-create"),
    path("clients/<int:pk>/", views.ClientDetailAPIView.as_view(), name="client-detail"),
]
