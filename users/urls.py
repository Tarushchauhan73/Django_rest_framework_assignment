
from django.urls import path
from . import views
from .views import ProfileListView

urlpatterns = [
    path("users/", views.UserListCreateView.as_view(), name="user-list-create"),
    path("users/<int:pk>/", views.UserDetailView.as_view(), name="user-detail"),
    path("profiles/", ProfileListView.as_view(), name="profile-list"),

    path("login/", views.LoginView.as_view(), name="login"),

    path("send-otp/", views.SendOTPView.as_view(), name="send-otp"),
    path("verify-otp/", views.VerifyOTPView.as_view(), name="verify-otp"),
    path("forgot-password/", views.ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password/", views.ResetPasswordView.as_view(), name="reset-password"),

    path("clients/", views.ClientListCreateAPIView.as_view(), name="client-list-create"),
    path("clients/<int:pk>/", views.ClientDetailAPIView.as_view(), name="client-detail"),

    path("projects/", views.ProjectListCreateView.as_view(), name="project-list-create"),
    path("projects/<int:pk>/", views.ProjectDetailView.as_view(), name="project-detail"),
]
