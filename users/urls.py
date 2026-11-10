
from django.urls import path
from . import views
from .views import ClientRestoreView, ProfileListView, ProjectRestoreView, UserRestoreView

urlpatterns = [
    path("users/", views.UserListCreateView.as_view(), name="user-list-create"),
    path("users/<int:pk>/", views.UserDetailView.as_view(), name="user-detail"),

    path("login/", views.LoginView.as_view(), name="login"),

    path("send-otp/", views.SendOTPView.as_view(), name="send-otp"),
    path("verify-otp/", views.VerifyOTPView.as_view(), name="verify-otp"),
    path("forgot-password/", views.ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password/", views.ResetPasswordView.as_view(), name="reset-password"),

    path("clients/", views.ClientListCreateAPIView.as_view(), name="client-list-create"),
   path(
    "clients/<int:pk>/",
    views.ClientDetailView.as_view(),
    name="client-detail"
),

    path("projects/", views.ProjectListCreateView.as_view(), name="project-list-create"),
    path("projects/<int:pk>/", views.ProjectDetailView.as_view(), name="project-detail"),

    path("profiles/", ProfileListView.as_view(), name="profile-list-create"),
    path("profiles/<int:pk>/", views.ProfileDetailView.as_view(), name="profile-detail"),


path(
    "projects/<int:project_id>/attachements/",
    views.ProjectAttachementListCreateView.as_view(),
    name="project-attachement-list-create",
),
path(
    "projects/<int:project_id>/attachements/<int:attachement_id>/",
    views.ProjectAttachementDetailView.as_view(),
    name="project-attachement-detail",
),

# Single restore
path(
    "users/restore/<int:pk>/",
    views.UserRestoreView.as_view(),
    name="user-restore"
),

path(
    "clients/restore/<int:pk>/",
    views.ClientRestoreView.as_view(),
    name="client-restore"
),

path(
    "projects/restore/<int:pk>/",
    views.ProjectRestoreView.as_view(),
    name="project-restore"
),

# Bulk restore
path(
    "users/restore/",
    views.UserRestoreView.as_view(),
    name="user-bulk-restore"
),

path(
    "clients/restore/",
    views.ClientRestoreView.as_view(),
    name="client-bulk-restore"
),

path(
    "projects/restore/",
    views.ProjectRestoreView.as_view(),
    name="project-bulk-restore"
),

path(
    "project-tasks/",
    views.ProjectTaskListCreateAPIView.as_view(),
    name="project-task-list-create"
),
path(
    "project-tasks/<int:pk>/",
    views.ProjectTaskDetailAPIView.as_view(),
    name="project-task-detail"
),
path(
    "project-task-comments/",
    views.ProjectTaskCommentListCreateAPIView.as_view(),
    name="project-task-comment-list-create"
),
path(
    "project-task-comments/<int:pk>/",
    views.ProjectTaskCommentDetailAPIView.as_view(),
    name="project-task-comment-detail"
),

path(
    "project-tasks/restore/",
    views.ProjectTaskRestoreView.as_view(),
    name="project-task-bulk-restore"
),
]
