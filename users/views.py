
import profile
from typing import Self

from django.contrib.auth import get_user_model
from django.db.migrations import serializer
from django.http import request
from django.test import client
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
import json
from django.utils import  timezone
from django.db.models import Q
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
from .utils import send_project_notifications
from .models import Project, ProjectAttachement, ProjectTask, ProjectTaskcomment
from .serializers import ProjectAttachementSerializer, ProjectTaskCommentSerializer, ProjectTaskSerializer
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
from .utils import send_project_notifications

User = get_user_model()



# USER LIST AND CREATE
# GET  /api/users/
# POST /api/users/

class UserListCreateView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        users = User.objects.all()

        search = request.query_params.get("search", "").strip()

        if search.lower() == "inactive":
            users = users.filter(status__iexact="Inactive")

        elif search.lower() == "active":
            users = users.filter(status__iexact="Active")

        else:
          
            users = users.filter(status="Active")

            if search:
                users = users.filter(
                    Q(username__icontains=search) |
                    Q(first_name__icontains=search) |
                    Q(last_name__icontains=search) |
                    Q(email__icontains=search) |
                    Q(phone__icontains=search) |
                    Q(nationality__icontains=search) |
                    Q(profiles__name__icontains=search)
                )

      
        profile_id = request.query_params.get("profile_id")

        if profile_id:
            users = users.filter(profiles_id=profile_id)

     
        role = request.query_params.get("role")

        if role:
            users = users.filter(
                profiles__name__iexact=role.strip()
            )

        
        first_name = request.query_params.get("first_name")

        if first_name:
            users = users.filter(
                first_name__icontains=first_name
            )

      
        last_name = request.query_params.get("last_name")

        if last_name:
            users = users.filter(
                last_name__icontains=last_name
            )

        
        email = request.query_params.get("email")

        if email:
            users = users.filter(email__icontains=email)

    
        phone = request.query_params.get("phone")

        if phone:
            users = users.filter(phone__icontains=phone)

        
        nationality = request.query_params.get("nationality")

        if nationality:
            users = users.filter(
                nationality__icontains=nationality
            )

    
        gender = request.query_params.get("gender")

        if gender:
            users = users.filter(gender__iexact=gender)

        users = users.order_by("id").distinct()

      
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

    def patch(self, request, pk=None):
        # Bulk restore
        if pk is None:
            user_ids = request.data.get("user_ids")

            if not isinstance(user_ids, list) or not user_ids:
                return Response(
                    {"error": "Please provide a non-empty user_ids list."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            users = User.objects.filter(
                pk__in=user_ids,
                status="Inactive"
            )

            restored_users = []

            for user in users:
                user.status = "Active"
                user.save(update_fields=["status"])
                restored_users.append(user)

            return Response(
                {
                    "message": "Users restored successfully.",
                    "restored_count": len(restored_users),
                    "users": UserSerializer(
                        restored_users, many=True
                    ).data
                },
                status=status.HTTP_200_OK
            )

        # Single restore
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



class ProjectTaskListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        tasks = ProjectTask.objects.select_related(
            "project",
            "assigned_to",
            "assigned_to__profiles",
            "assigned_by",
            "assigned_by__profiles",
            "created_by",
            "created_by__profiles",
            "updated_by",
            "updated_by__profiles"
        ).all()

   
        is_deleted = request.query_params.get("is_deleted")

        if is_deleted is not None:
            if is_deleted.lower() in ["true", "1"]:
                tasks = tasks.filter(is_deleted=True)
            elif is_deleted.lower() in ["false", "0"]:
                tasks = tasks.filter(is_deleted=False)
        else:
            tasks = tasks.filter(is_deleted=False)

    
        task_id = request.query_params.get("id")
        if task_id:
            tasks = tasks.filter(id=task_id)

       
        title = request.query_params.get("title")
        if title:
            tasks = tasks.filter(title__icontains=title)

    
        project_id = request.query_params.get("project_id")
        if project_id:
            tasks = tasks.filter(project_id=project_id)

        
        project_title = request.query_params.get("project_title")
        if project_title:
            tasks = tasks.filter(project__title__icontains=project_title)

       
        assigned_to = request.query_params.get("assigned_to")
        if assigned_to:
            tasks = tasks.filter(assigned_to_id=assigned_to)

        
        assigned_to_first_name = request.query_params.get("assigned_to_first_name")
        if assigned_to_first_name:
            tasks = tasks.filter(
                assigned_to__first_name__icontains=assigned_to_first_name
            )

        
        assigned_to_last_name = request.query_params.get("assigned_to_last_name")
        if assigned_to_last_name:
            tasks = tasks.filter(
                assigned_to__last_name__icontains=assigned_to_last_name
            )

      
        assigned_to_email = request.query_params.get("assigned_to_email")
        if assigned_to_email:
            tasks = tasks.filter(
                assigned_to__email__icontains=assigned_to_email
            )

     
        assigned_to_profile = request.query_params.get("assigned_to_profile")
        if assigned_to_profile:
            tasks = tasks.filter(
                assigned_to__profiles__name__icontains=assigned_to_profile
            )

       
        assigned_by = request.query_params.get("assigned_by")
        if assigned_by:
            tasks = tasks.filter(assigned_by_id=assigned_by)

        
        assigned_by_first_name = request.query_params.get("assigned_by_first_name")
        if assigned_by_first_name:
            tasks = tasks.filter(
                assigned_by__first_name__icontains=assigned_by_first_name
            )

   
        assigned_by_last_name = request.query_params.get("assigned_by_last_name")
        if assigned_by_last_name:
            tasks = tasks.filter(
                assigned_by__last_name__icontains=assigned_by_last_name
            )

 
        assigned_by_email = request.query_params.get("assigned_by_email")
        if assigned_by_email:
            tasks = tasks.filter(
                assigned_by__email__icontains=assigned_by_email
            )

    
        start_date = request.query_params.get("start_date")
        if start_date:
            tasks = tasks.filter(start_date=start_date)

   
        completion_date = request.query_params.get("completion_date")
        if completion_date:
            tasks = tasks.filter(completion_date=completion_date)

   
        deadline_date = request.query_params.get("deadline_date")
        if deadline_date:
            tasks = tasks.filter(deadline_date=deadline_date)

      
        status_filter = request.query_params.get("status")
        if status_filter:
            tasks = tasks.filter(status__iexact=status_filter)

      
        created_by = request.query_params.get("created_by")
        if created_by:
            tasks = tasks.filter(created_by_id=created_by)

   
        created_by_first_name = request.query_params.get("created_by_first_name")
        if created_by_first_name:
            tasks = tasks.filter(
                created_by__first_name__icontains=created_by_first_name
            )

     
        created_by_email = request.query_params.get("created_by_email")
        if created_by_email:
            tasks = tasks.filter(
                created_by__email__icontains=created_by_email
            )


        updated_by = request.query_params.get("updated_by")
        if updated_by:
            tasks = tasks.filter(updated_by_id=updated_by)

  
        updated_by_first_name = request.query_params.get("updated_by_first_name")
        if updated_by_first_name:
            tasks = tasks.filter(
                updated_by__first_name__icontains=updated_by_first_name
            )

   
        updated_by_email = request.query_params.get("updated_by_email")
        if updated_by_email:
            tasks = tasks.filter(
                updated_by__email__icontains=updated_by_email
            )

       
        created_at = request.query_params.get("created_at")
        if created_at:
            tasks = tasks.filter(created_at__date=created_at)

        updated_at = request.query_params.get("updated_at")
        if updated_at:
            tasks = tasks.filter(updated_at__date=updated_at)


        search = request.query_params.get("search")

        if search:
            tasks = tasks.filter(
                Q(title__icontains=search) |
                Q(status__icontains=search) |
                Q(project__title__icontains=search) |

                Q(assigned_to__first_name__icontains=search) |
                Q(assigned_to__last_name__icontains=search) |
                Q(assigned_to__email__icontains=search) |
                Q(assigned_to__profiles__name__icontains=search) |

                Q(assigned_by__first_name__icontains=search) |
                Q(assigned_by__last_name__icontains=search) |
                Q(assigned_by__email__icontains=search) |

                Q(created_by__first_name__icontains=search) |
                Q(created_by__last_name__icontains=search) |
                Q(created_by__email__icontains=search) |

                Q(updated_by__first_name__icontains=search) |
                Q(updated_by__last_name__icontains=search) |
                Q(updated_by__email__icontains=search)
            )

        tasks = tasks.order_by("id").distinct()

        serializer = ProjectTaskSerializer(tasks, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):

        print("Logged-in User ID:", request.user.id)
        print("Logged-in Username:", request.user.username)
        print(
            "Logged-in Profile:",
            request.user.profiles.name if request.user.profiles else None
        )

        serializer = ProjectTaskSerializer(data=request.data)

        if serializer.is_valid():

            # Get the selected project from the request
            project = serializer.validated_data["project"]

            # Get the manager assigned to that project
            assigned_by_user = project.manager

            serializer.save(
                created_by=request.user,
                updated_by=request.user,
                assigned_by=project.manager
            )

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

class ProjectTaskDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return ProjectTask.objects.filter(pk=pk).first()

    def get(self, request, pk):
        task = self.get_object(pk)

        if task is None:
            return Response({"error": "Task not found."}, status=404)

        return Response(ProjectTaskSerializer(task).data, status=200)

    def put(self, request, pk):
        return self.update_task(request, pk, partial=False)

    def patch(self, request, pk):
        return self.update_task(request, pk, partial=True)

    def update_task(self, request, pk, partial):
        task = self.get_object(pk)

        if task is None:
            return Response({"error": "Task not found."}, status=404)

        serializer = ProjectTaskSerializer(
            task,
            data=request.data,
            partial=partial
        )

        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return Response(
                {
                    "message": "Task updated successfully.",
                    "task": serializer.data
                },
                status=200
            )

        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        task = self.get_object(pk)

        if task is None:
            return Response({"error": "Task not found."}, status=404)

        task.delete()
        return Response(
            {"message": "Task deleted successfully."},
            status=200
        )


class ProjectTaskCommentListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        comments = ProjectTaskcomment.objects.select_related(
            "project_task", "project", "commented_by"
        ).all()

        task_id = request.query_params.get("task_id")
        project_id = request.query_params.get("project_id")
        user_id = request.query_params.get("user_id")
        search = request.query_params.get("search")

        if task_id:
            comments = comments.filter(project_task_id=task_id)

        if project_id:
            comments = comments.filter(project_id=project_id)

        if user_id:
            comments = comments.filter(commented_by_id=user_id)

        if search:
            comments = comments.filter(
                Q(comment__icontains=search) |
                Q(project_task__title__icontains=search) |
                Q(project__title__icontains=search)
            )

        comments = comments.order_by("-created_at").distinct()

        serializer = ProjectTaskCommentSerializer(comments, many=True)
        return Response(serializer.data, status=200)

    def post(self, request):
        serializer = ProjectTaskCommentSerializer(data=request.data)

        if serializer.is_valid():
            comment = serializer.save(commented_by=request.user)
            return Response(
                {
                    "message": "Comment added successfully.",
                    "comment": ProjectTaskCommentSerializer(comment).data
                },
                status=201
            )

        return Response(serializer.errors, status=400)


class ProjectTaskCommentDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return ProjectTaskcomment.objects.filter(pk=pk).first()

    def get(self, request, pk):
        comment = self.get_object(pk)

        if comment is None:
            return Response({"error": "Comment not found."}, status=404)

        return Response(ProjectTaskCommentSerializer(comment).data, status=200)

    def put(self, request, pk):
        return self.update_comment(request, pk, partial=False)

    def patch(self, request, pk):
        return self.update_comment(request, pk, partial=True)

    def update_comment(self, request, pk, partial):
        comment = self.get_object(pk)

        if comment is None:
            return Response({"error": "Comment not found."}, status=404)

        serializer = ProjectTaskCommentSerializer(
            comment,
            data=request.data,
            partial=partial
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Comment updated successfully.",
                    "comment": serializer.data
                },
                status=200
            )

        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        comment = self.get_object(pk)

        if comment is None:
            return Response({"error": "Comment not found."}, status=404)

        comment.delete()
        return Response(
            {"message": "Comment deleted successfully."},
            status=200
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
        clients = Client.objects.all()

        fname = request.query_params.get("fname")
        lname = request.query_params.get("lname")
        email = request.query_params.get("email")
        contactno = request.query_params.get("contactno")
        country = request.query_params.get("country")
        address = request.query_params.get("address")
        client_status = request.query_params.get("status")

        if fname:
            clients = clients.filter(fname__icontains=fname)

        if lname:
            clients = clients.filter(lname__icontains=lname)

        if email:
            clients = clients.filter(email__icontains=email)

        if contactno:
            clients = clients.filter(contactno__icontains=contactno)

        if country:
            clients = clients.filter(country__icontains=country)

        if address:
            clients = clients.filter(address__icontains=address)

        if client_status:
            clients = clients.filter(status__iexact=client_status)

        # General search across multiple fields
        search = request.query_params.get("search")

        if search:
            clients = clients.filter(
                  Q(fname__icontains=search)
                 | Q(lname__icontains=search)
                | Q(email__icontains=search)
                | Q(contactno__icontains=search)
                | Q(country__icontains=search)
                | Q(address__icontains=search)
            )

        # Remove duplicates and order results
        clients = clients.order_by("id").distinct()

        paginator = PageNumberPagination()
        paginator.page_size = 100
        page = paginator.paginate_queryset(clients, request, view=self)

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

class ClientDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        client = Client.objects.filter(
            pk=pk,
            status="Active"
        ).first()

        if client is None:
            return Response(
                {"error": "Client not found or already inactive."},
                status=status.HTTP_404_NOT_FOUND
            )

        client.status = "Inactive"
        client.updated_by = request.user
        client.save()

        return Response(
            {"message": "Client soft-deleted successfully."},
            status=status.HTTP_200_OK
        )

class ClientRestoreView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk=None):
        # Bulk restore
        if pk is None:
            client_ids = request.data.get("client_ids")

            if not isinstance(client_ids, list) or not client_ids:
                return Response(
                    {"error": "Please provide a non-empty client_ids list."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            clients = Client.objects.filter(
                pk__in=client_ids,
                status="Inactive"
            )

            restored_clients = []

            for client in clients:
                client.status = "Active"
                client.updated_by = request.user
                client.save()
                restored_clients.append(client)

            return Response(
                {
                    "message": "Clients restored successfully.",
                    "restored_count": len(restored_clients),
                    "clients": ClientSerializer(
                        restored_clients, many=True
                    ).data
                },
                status=status.HTTP_200_OK
            )

        # Single restore
        client = Client.objects.filter(
            pk=pk,
            status="Inactive"
        ).first()

        if client is None:
            return Response(
                {"error": "Client not found or already active."},
                status=status.HTTP_404_NOT_FOUND
            )

        client.status = "Active"
        client.updated_by = request.user
        client.save()

        return Response(
            {
                "message": "Client restored successfully.",
                "client": ClientSerializer(client).data
            },
            status=status.HTTP_200_OK
        )
# PROJECT LIST AND CREATE



class ProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        user = self.request.user

        # 1. Authentication check
        if not user.is_authenticated:
            return Project.objects.none()

      
        profile = getattr(user, "profiles", None)

        if profile is None:
            return Project.objects.none()

        user_role = profile.name.strip().lower()


        is_deleted = self.request.query_params.get(
            "is_deleted", "false"
        ).strip().lower()

        if is_deleted == "true":
            projects = Project.objects.filter(is_deleted=True)
        elif is_deleted == "false":
            projects = Project.objects.filter(is_deleted=False)
        else:
            return Project.objects.none()

      
        if user_role in ["superadmin", "admin"]:
            pass
        elif user_role == "manager":
            projects = projects.filter(manager=user)
        else:
            return Project.objects.none()

      
        search = self.request.query_params.get("search", "").strip()

        if search:
            projects = projects.filter(
                Q(title__icontains=search) |
                Q(manager__username__icontains=search) |
                Q(manager__first_name__icontains=search) |
                Q(manager__last_name__icontains=search) |
                Q(manager__email__icontains=search) |
                Q(client__fname__icontains=search) |
                Q(client__lname__icontains=search) |
                Q(client__email__icontains=search) |
                Q(type__icontains=search)
            )

       
        manager_id = self.request.query_params.get("manager_id", "").strip()
        if manager_id:
            projects = projects.filter(manager_id=manager_id)

      
        manager_first_name = self.request.query_params.get(
            "manager_first_name", ""
        ).strip()
        if manager_first_name:
            projects = projects.filter(
                manager__first_name__icontains=manager_first_name
            )

     
        manager_last_name = self.request.query_params.get(
            "manager_last_name", ""
        ).strip()
        if manager_last_name:
            projects = projects.filter(
                manager__last_name__icontains=manager_last_name
            )

        manager_email = self.request.query_params.get(
            "manager_email", ""
        ).strip()
        if manager_email:
            projects = projects.filter(
                manager__email__iexact=manager_email
            )

  
        client_id = self.request.query_params.get("client_id", "").strip()
        if client_id:
            projects = projects.filter(client_id=client_id)

        client_first_name = self.request.query_params.get(
            "client_first_name", ""
        ).strip()
        if client_first_name:
            projects = projects.filter(
                client__fname__icontains=client_first_name
            )

      
        client_last_name = self.request.query_params.get(
            "client_last_name", ""
        ).strip()
        if client_last_name:
            projects = projects.filter(
                client__lname__icontains=client_last_name
            )

       
        client_email = self.request.query_params.get(
            "client_email", ""
        ).strip()
        if client_email:
            projects = projects.filter(
                client__email__icontains=client_email
            )

       
        project_status = self.request.query_params.get("status", "").strip()
        if project_status:
            projects = projects.filter(status__iexact=project_status)

       
        project_type = self.request.query_params.get("type", "").strip()
        if project_type:
            projects = projects.filter(type__iexact=project_type)

      
        manager_role = self.request.query_params.get("role", "").strip()
        if manager_role:
            projects = projects.filter(
                manager__profiles__name__iexact=manager_role
            )

        return projects.order_by("created_at").distinct()


    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)

        if response.status_code == 201:
            response.data["email_notifications"] = getattr(
                self,
                "notification_results",
                {},
            )

        return response
    

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

    def patch(self, request, pk=None):
        # Bulk restore
        if pk is None:
            project_ids = request.data.get("project_ids")

            if not isinstance(project_ids, list) or not project_ids:
                return Response(
                    {"error": "Please provide a non-empty project_ids list."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            projects = Project.objects.filter(
                pk__in=project_ids,
                is_deleted=True
            )

            restored_projects = []

            for project in projects:
                project.is_deleted = False
                project.deleted_at = None
                project.deleted_by = None

                project.save(
                    update_fields=[
                        "is_deleted",
                        "deleted_at",
                        "deleted_by"
                    ]
                )

                restored_projects.append(project)

            return Response(
                {
                    "message": "Projects restored successfully.",
                    "restored_count": len(restored_projects),
                    "projects": ProjectSerializer(
                        restored_projects,
                        many=True,
                        context={"request": request}
                    ).data
                },
                status=status.HTTP_200_OK
            )

        # Single restore
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
        "superadmin",
        "admin",
        "manager",
        "teamleader",
        "developer",
        "HR"
    ]

    def get(self, request):
        profiles = Profile.objects.filter(
            is_active=True
        ).order_by("id")

        serializer = ProfileSerializer(profiles, many=True)
        return Response(serializer.data)

    def post(self, request):
     role = request.data.get("role")

     if not role or not isinstance(role, str):
        return Response(
            {"error": "Role is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

     role = role.strip()

   
     if Profile.objects.filter(name__iexact=role).exists():
        return Response(
            {"error": "This profile already exists."},
            status=status.HTTP_400_BAD_REQUEST
        )

     serializer = ProfileSerializer(
        data={"role": role}
    )

     serializer.is_valid(raise_exception=True)

   
     is_default = role.casefold() in {
        name.casefold() for name in self.DEFAULT_PROFILES
    }

     profile = serializer.save(
        is_default=is_default,
        is_active=True
    )

     return Response(
        ProfileSerializer(profile).data,
        status=status.HTTP_201_CREATED
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
     project = Project.objects.filter(pk=pk).first()

     if not project:
        return Response(
            {"error": "Project not found."},
            status=status.HTTP_404_NOT_FOUND
        )

     attachment_ids = request.data.get("attachment_ids")
     delete_all = request.data.get("delete_all_attachments", False)


    # Convert form-data string into a Boolean
     if isinstance(delete_all, str):
        delete_all = delete_all.lower() in ["true", "1", "yes"]

   
     if delete_all:
        attachments = project.attachments.all()

     elif attachment_ids is not None:

      
        if isinstance(attachment_ids, str):
            try:
                attachment_ids = json.loads(attachment_ids)
            except json.JSONDecodeError:
                return Response(
                    {"error": "Invalid attachment IDs format."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if not isinstance(attachment_ids, list) or not attachment_ids:
            return Response(
                {"error": "Provide a non-empty list of attachment IDs."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            attachment_ids = list(set(int(i) for i in attachment_ids))
        except (ValueError, TypeError):
            return Response(
                {"error": "All attachment IDs must be integers."},
                status=status.HTTP_400_BAD_REQUEST
            )

        attachments = project.attachments.filter(
            id__in=attachment_ids
        )

        if attachments.count() != len(attachment_ids):
            return Response(
                {
                    "error": "One or more attachments were not found in this project."
                },
                status=status.HTTP_404_NOT_FOUND
            )

     else:
        # Soft-delete the entire project
        project.is_deleted = True
        project.deleted_at = timezone.now()
        project.deleted_by = request.user
        project.save()

        return Response(
            {
                "message": f"Project {project.id} soft deleted successfully."
            },
            status=status.HTTP_200_OK
        )

    # Delete physical files and database records
     deleted_count = attachments.count()

     for attachment in attachments:
        if attachment.file:
            attachment.file.delete(save=False)

     attachments.delete()

     return Response(
        {
            "message": "Attachments deleted successfully.",
            "deleted_count": deleted_count
        },
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
    parser_classes = [JSONParser, MultiPartParser, FormParser]

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

class ProjectTaskRestoreView(APIView):

    permission_classes = [IsAuthenticated]

    def patch(self, request):

        project_task_ids = request.data.get("project_task_ids", [])

        if not project_task_ids:
            return Response(
                {"error": "Please provide project_task_ids."},
                status=status.HTTP_400_BAD_REQUEST
            )

        tasks = ProjectTask.objects.filter(
            id__in=project_task_ids,
            is_deleted=True
        )

        restored_count = tasks.update(is_deleted=False)

        return Response(
            {
                "message": "Project tasks restored successfully.",
                "restored_count": restored_count
            },
            status=status.HTTP_200_OK
        )

