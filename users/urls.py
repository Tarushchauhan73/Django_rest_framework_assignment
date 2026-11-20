
from django.urls import path
from . import views
from .views import ProfileListView, ProjectTaskCommentListCreateAPIView

urlpatterns = [

    #  USER URLS

    path(
        "users/",
        views.UserListCreateView.as_view(),
        name="user-list-create"
    ),

    # User restore
    path(
        "users/restore/",
        views.UserRestoreView.as_view(),
        name="user-restore"
    ),

    # User detail
    path(
        "users/<str:pk>/",
        views.UserDetailView.as_view(),
        name="user-detail"
    ),

    # AUTHENTICATION URLS 

    path("login/", views.LoginView.as_view(), name="login"),

    path("send-otp/", views.SendOTPView.as_view(), name="send-otp"),

    path("verify-otp/", views.VerifyOTPView.as_view(), name="verify-otp"),

    path("forgot-password/", views.ForgotPasswordView.as_view(), name="forgot-password"),

    path("reset-password/", views.ResetPasswordView.as_view(), name="reset-password"),

    #  CLIENT URLS 

    path(
        "clients/",
        views.ClientListCreateAPIView.as_view(),
        name="client-list-create"
    ),

    # Client single restore
    path(
        "clients/restore/<int:pk>/",
        views.ClientRestoreView.as_view(),
        name="client-restore"
    ),

    # Client bulk restore
    path(
        "clients/restore/",
        views.ClientRestoreView.as_view(),
        name="client-bulk-restore"
    ),

    # Client detail
    path(
        "clients/<str:pk>/",
        views.ClientDetailAPIView.as_view(),
        name="client-detail"
    ),

    # PROJECT URLS 

    path(
        "projects/",
        views.ProjectListCreateView.as_view(),
        name="project-list-create"
    ),

    # Project single restore
    path(
        "projects/restore/<int:pk>/",
        views.ProjectRestoreView.as_view(),
        name="project-restore"
    ),

    # Project bulk restore
    path(
        "projects/restore/",
        views.ProjectRestoreView.as_view(),
        name="project-bulk-restore"
    ),

    # Project detail
    path(
        "projects/<str:pk>/",
        views.ProjectDetailView.as_view(),
        name="project-detail"
    ),

    #  PROJECT ATTACHMENT URLS

    path(
        "projects/<int:project_id>/attachements/",
        views.ProjectAttachementListCreateView.as_view(),
        name="project-attachement-list-create"
    ),

    path(
        "projects/<int:project_id>/attachements/<int:attachement_id>/",
        views.ProjectAttachementDetailView.as_view(),
        name="project-attachement-detail"
    ),

    #  PROFILE URLS

    path(
        "profiles/",
        ProfileListView.as_view(),
        name="profile-list-create"
    ),

    path(
        "profiles/<str:pk>/",
        views.ProfileDetailView.as_view(),
        name="profile-detail"
    ),

    #  PROJECT TASK URLS 

    path(
        "project-tasks/",
        views.ProjectTaskListCreateAPIView.as_view(),
        name="project-task-list-create"
    ),

    # Project Task bulk restore
    path(
        "project-tasks/restore/",
        views.ProjectTaskRestoreView.as_view(),
        name="project-task-bulk-restore"
    ),

    # Project Task detail
    path(
        "project-tasks/<str:pk>/",
        views.ProjectTaskDetailAPIView.as_view(),
        name="project-task-detail"
    ),

    #  PROJECT TASK COMMENT URLS 
    path(
    "project-task-comments/",
    ProjectTaskCommentListCreateAPIView.as_view(),
    name="project-task-comment-list"
),

    path(
        "project-task-comments/<str:pk>/",
        views.ProjectTaskCommentListCreateAPIView.as_view(),
        name="project-task-comment-list-create"
    ),

    path(
        "project-task-comments/<str:pk>/",
        views.ProjectTaskCommentDetailAPIView.as_view(),
        name="project-task-comment-detail"
    ),

]
