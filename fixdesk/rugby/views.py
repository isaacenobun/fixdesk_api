import os
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from fixdesk_api.models import Organization
from fixdesk.utils.microsoft import verify_microsoft_token

import boto3
from django.conf import settings
import uuid

from dotenv import load_dotenv
load_dotenv()

from django.contrib.auth import get_user_model
User = get_user_model()

# from .tasks import send_mail
from .mailer import send_mail

from .models import Issues, Payment, Tasks, Comments, Departments, ActivityLog, Milestone, LeaveRequest, FacilityRequest, ProcurementRequest, Comments_Requests

from .serializers import MyTokenObtainPairSerializer, UserSerializer, IssuesSerializer, PaymentSerializer, TasksSerializer, CommentsSerializer, DepartmentsSerializer, ActivityLogSerializer, MilestoneSerializer, LeaveRequestSerializer, FacilityRequestSerializer, ProcurementRequestSerializer, Comments_RequestsSerializer

from .inclusion_matrix import users_inclusion_matrix as inclusion_matrix
from .approval_matrix import approval_matrix, attach_approvers_to_approval_info, extract_approval_emails

@api_view(["POST"])
def generate_upload_url(request):
    id = request.data.get("id")
    type = request.data.get("type")
    s3 = boto3.client(
        "s3",
        region_name=settings.AWS_S3_REGION_NAME,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )

    file_type = request.data.get("file_type")
    original_name = request.data.get("file_name")

    unique_name = f"{uuid.uuid4()}_{original_name}"

    key = f"rugby/{unique_name}"

    presigned_url = s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
            "Key": key,
            "ContentType": file_type,
        },
        ExpiresIn=3600,
    )

    file_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{key}"

    objects = {
        "issue": Issues,
        "facility": FacilityRequest,
        "procurement": ProcurementRequest,
    }

    obj = objects[type].objects.get(id=id)
    obj.attachment = file_url
    obj.attachment_key = key
    obj.save()

    return Response({
        "upload_url": presigned_url,
        "file_key": key,
        "file_url": file_url,
    })

@api_view(["POST"])
@permission_classes([AllowAny])
def microsoft_login(request):
    id_token = request.data.get("id_token")
    subdomain = request.data.get("subdomain")

    if not id_token or not subdomain:
        return Response({"detail": "Missing data"}, status=400)

    try:
        payload = verify_microsoft_token(id_token)
    except Exception:
        return Response({"detail": "Invalid token"}, status=401)

    email = payload.get("preferred_username") or payload.get("email")

    if not email:
        return Response({"detail": "No email found"}, status=400)

    # Extract domain
    email_domain = email.split("@")[-1].lower()

    try:
        school = Organization.objects.get(subdomain=subdomain)
    except Organization.DoesNotExist:
        return Response({"detail": "School not found"}, status=404)

    # 🔒 Domain restriction
    if email_domain != school.allowed_email_domain.lower():
        return Response(
            {"detail": "Unauthorized email domain"},
            status=status.HTTP_403_FORBIDDEN
        )

    # Create / get user
    user, _ = User.objects.get(
        email=email,
        defaults={"email": email}
    )

    # Issue JWT
    refresh = RefreshToken.for_user(user)

    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "email": email
    })

class MyTokenObtainPairView(TokenObtainPairView):
    """
    Custom TokenObtainPairView using MyTokenObtainPairSerializer.
    """
    serializer_class = MyTokenObtainPairSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['email']
    
class DepartmentsViewSet(viewsets.ModelViewSet):
    queryset = Departments.objects.all()
    serializer_class = DepartmentsSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name']

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']

class ActivityLogViewSet(viewsets.ModelViewSet):
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        activity_log = serializer.save()

        type, action, id = activity_log.type.split('_')

        users = inclusion_matrix(
            email=activity_log.user.email,
            User_model=User,
            role=activity_log.user.role,
            department=activity_log.user.department,
            subject=type,
            action=action,
            id=id
        )

        hasher = {'issue': Issues,
                'task': Tasks,
                'facilityrequest': FacilityRequest,
                'procurementrequest': ProcurementRequest,
                'leaverequest': LeaveRequest}

        hasher[type].objects.get(id=id).activity.add(activity_log)

        obj = hasher[type].objects.get(id=id)

        context = {
            'id': f'{id[:3]}',
            'user': activity_log.user.first_name + ' ' + activity_log.user.last_name,
            'title': getattr(obj, 'title', None),
            'description': getattr(obj, 'description', None),
            'date': activity_log.timestamp,
            'due_date': getattr(obj, 'due_date', None),
            'previous_status': request.data.get('previous_status', None),
            'status': getattr(obj, 'status', None),
            'reported_by': obj.reported_by.first_name or obj.requested_by.first_name + ' ' + obj.reported_by.last_name or obj.requested_by.last_name,
            'priority': getattr(obj, 'priority', None),
            'assigned_to': getattr(obj, 'assigned_to', None)
        }

        subject_hash = {
            f'{type}_creation': f'New {type.capitalize()} Created',
            f'{type}_status': f'{type.capitalize()} Status Update',
            f'{type}_assigned': f'{type.capitalize()} Assigned to You',
            f'{type}_comment': f'New comment on {type.capitalize()}',
        }

        print (type, action)

        send_mail(
                subject=subject_hash[f'{type}_{action}'],
                to_email=list(users),
                context=context,
                type=type,
                action=action
        )

        return Response(
            self.get_serializer(activity_log).data,
            status=status.HTTP_201_CREATED
        )
    
    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)

        activity_log = self.get_object()

        type, action, id = request.data.get('type').split("_")

        users = inclusion_matrix(
            email=activity_log.user.email,
            User_model=User,
            role=activity_log.user.role,
            department=activity_log.user.department,
            subject=type,
            action=action,
            id=id
        )

        hasher = {'issue': Issues,
                'task': Tasks,
                'facilityrequest': FacilityRequest,
                'procurementrequest': ProcurementRequest,
                'leaverequest': LeaveRequest}

        related_obj = hasher[type].objects.get(id=id)

        context = {
            'id': f'{id[:3]}',
            'user': activity_log.user.first_name + ' ' + activity_log.user.last_name,
            'title': related_obj.title,
            'description': related_obj.description,
            'date': activity_log.timestamp,
            'due_date': getattr(related_obj, 'due_date', None),
            'previous_status': request.data.get('previous_status', None),
            'status': getattr(related_obj, 'status', None),
            'reported_by': related_obj.reported_by.first_name + ' ' + related_obj.reported_by.last_name,
            'priority': getattr(related_obj, 'priority', None),
            'assigned_to': getattr(related_obj, 'assigned_to', None)
        }

        subject_hash = {
            f'{type}_creation': f'New {type.capitalize()} Created',
            f'{type}_status': f'{type.capitalize()} Status Update',
            f'{type}_assigned': f'{type.capitalize()} Assigned to You',
            f'{type}_comment': f'New comment on {type.capitalize()}',
        }

        send_mail(
                subject=subject_hash[f'{type}_{action}'],
                to_email=list(users),
                context=context,
                type=type,
                action=action
        )

        return response

class MilestoneViewSet(viewsets.ModelViewSet):
    queryset = Milestone.objects.all()
    serializer_class = MilestoneSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        milestone = serializer.save()

        user = User.objects.get(id=request.data.get('user_id'))

        activity_log = ActivityLog.objects.create(
            user=user,
            type=f'milestone_creation_{milestone.id}',
            text=f"Created milestone {milestone.title}"
        )

        type = activity_log.type

        subject = type.split("_")[0]
        action = type.split("_")[1]
        id = type.split("_")[2]

        users = inclusion_matrix(
            email=activity_log.user.email,
            User_model=User,
            role=user.role,
            department=user.department,
            subject=subject,
            action=action,
            id=id
        )

        context = {
        }

        # send email to users
        send_mail(
                subject=f"New Milestone Created",
                to_email=list(users),
                context=context,
                type="milestone"
        )

        return Response(
            self.get_serializer(milestone).data,
            status=status.HTTP_201_CREATED
        )

    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)

        milestone = self.get_object()
        user = User.objects.get(id=request.data.get('user_id'))

        activity_log = ActivityLog.objects.create(
            user=user,
            type=f'milestone_status_change_{milestone.id}',
            text=f"Updated milestone {milestone.title}"
        )

        type = activity_log.type

        subject = type.split("_")[0]
        action = type.split("_")[1]
        id = type.split("_")[2]

        users = inclusion_matrix(
            email=activity_log.user.email,
            User_model=User,
            role=user.role,
            department=user.department,
            subject=subject,
            action=action,
            id=id
        )

        context = {
        }

        # send email to users
        send_mail(
                subject=f"Milestone Updated",
                to_email=list(users),
                context=context,
                type="milestone"
        )

        return response

class IssuesViewSet(viewsets.ModelViewSet):
    queryset = Issues.objects.all()
    serializer_class = IssuesSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['reported_by', 'status', 'priority', 'type']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        issue = serializer.save()

        activity_log = ActivityLog.objects.create(
            user=issue.reported_by,
            type=f'issue_creation_{issue.id}',
            text=f"{issue.reported_by.first_name} {issue.reported_by.last_name} Created IT Ticket"
        )

        issue.activity.add(activity_log)

        type = activity_log.type
        subject = type.split("_")[0]
        action = type.split("_")[1]
        id = type.split("_")[2]

        users = inclusion_matrix(
            email=activity_log.user.email,
            User_model=User,
            role=activity_log.user.role,
            department=activity_log.user.department,
            subject=subject,
            action=action,
            id=id
        )

        context = {
            'id': f'{id[:3]}',
            'title': issue.title,
            'description': issue.description,
            'date': issue.created_at
        }

        # send email to users
        send_mail(
                subject=f"New Issue Created",
                to_email=list(users),
                context=context,
                type="issue",
                action="creation"
        )

        return Response(
            self.get_serializer(issue).data,
            status=status.HTTP_201_CREATED
        )

class TasksViewSet(viewsets.ModelViewSet):
    queryset = Tasks.objects.all()
    serializer_class = TasksSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'priority']
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = serializer.save()

        activity_log = ActivityLog.objects.create(
            user=task.assigned_by,
            type=f'task_creation_{task.id}',
            text=f"Created task and assigned to {', '.join([user.first_name for user in task.assigned_to.all()])}"
        )

        task.activity.add(activity_log)
        
        milestones = request.data.get('milestones', [])
        if milestones:
            task.milestones.add(*milestones)

        type = activity_log.type
        subject = type.split("_")[0]
        action = type.split("_")[1]
        id = type.split("_")[2]

        users = inclusion_matrix(
            email=activity_log.user.email,
            User_model=User,
            role=activity_log.user.role,
            department=activity_log.user.department,
            subject=subject,
            action=action,
            id=id
        )

        context = {
            'id': f'{id[:3]}',
            'title': task.title,
            'description': task.description,
            'date': task.created_at
        }

        send_mail(
                subject=f"New Task Created",
                to_email=list(users),
                context=context,
                type="task",
                action="creation"
        )

        return Response(
            self.get_serializer(task).data,
            status=status.HTTP_201_CREATED
        )

class CommentsViewSet(viewsets.ModelViewSet):
    queryset = Comments.objects.all()
    serializer_class = CommentsSerializer
    http_method_names = ['get', 'post']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['commenter__email']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = serializer.save()

        type = request.data.get('type')

        activity_log = ActivityLog.objects.create(
            user=comment.commenter,
            type=type,
            text=f"{comment.commenter.first_name} {comment.commenter.last_name} commented on {type.split('_')[0]} {comment.case.id}"
        )

        type = activity_log.type
        subject = type.split("_")[0]
        action = type.split("_")[1]
        id = type.split("_")[2]

        users = inclusion_matrix(
            email=activity_log.user.email,
            User_model=User,
            role=activity_log.user.role,
            department=activity_log.user.department,
            subject=subject,
            action=action,
            id=id
        )

        hasher = {'issue': Issues,
                'task': Tasks}

        hasher[subject].objects.get(id=id).activity.add(activity_log)

        context = {
            'id': f'{id[:3]}',
            'title': comment.case.title,
            'description': comment.message,
            'date': comment.timestamp,
            'commenter': f'{comment.commenter.first_name} {comment.commenter.last_name}',
            'commenter_initial': f'{comment.commenter.first_name[0]}{comment.commenter.last_name[0]}'
        }

        send_mail(
                subject=f"New Comment on {subject}",
                to_email=list(users),
                context=context,
                type=subject,
                action="comment"
        )

        return Response(
            self.get_serializer(comment).data,
            status=status.HTTP_201_CREATED
        )

class Comments_RequestsViewSet(viewsets.ModelViewSet):
    queryset = Comments_Requests.objects.all()
    serializer_class = Comments_RequestsSerializer
    http_method_names = ['get', 'post']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['commenter__email']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = serializer.save()

        type = request.data.get('type')

        activity_log = ActivityLog.objects.create(
            user=comment.commenter,
            type=type,
            text=f"{comment.commenter.first_name} {comment.commenter.last_name} commented on {type.split('_')[0]} {comment.request.id}"
        )

        type = activity_log.type
        subject = type.split("_")[0]
        action = type.split("_")[1]
        id = type.split("_")[2]

        users = inclusion_matrix(
            email=activity_log.user.email,
            User_model=User,
            role=activity_log.user.role,
            department=activity_log.user.department,
            subject=subject,
            action=action,
            id=id
        )

        hasher = {'facilityrequest': FacilityRequest,
                'procurementrequest': ProcurementRequest,
                'leaverequest': LeaveRequest}

        hasher[subject].objects.get(id=id).activity.add(activity_log)

        context = {
            'id': f'{id[:3]}',
            'title': comment.request.reason,
            'description': comment.message,
            'date': comment.timestamp,
            'commenter': f'{comment.commenter.first_name} {comment.commenter.last_name}',
            'commenter_initial': f'{comment.commenter.first_name[0]}{comment.commenter.last_name[0]}'
        }

        send_mail(
                subject=f"New Comment on {subject}",
                to_email=list(users),
                context=context,
                type=subject,
                action=action
        )

        return Response(
            self.get_serializer(comment).data,
            status=status.HTTP_201_CREATED
        )

class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'type']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        leaveRequest = serializer.save()

        approval_info, levels = approval_matrix(
            "leaverequest",
            leaveRequest.requested_by.role,
            leaveRequest.requested_by.department
        )

        approval_info = attach_approvers_to_approval_info(
            approval_info=approval_info,
            requester=leaveRequest.requested_by,
            User_model=User
            )

        leaveRequest.approval_info = approval_info
        leaveRequest.save(update_fields=["approval_info"])

        approver_emails = extract_approval_emails(approval_info)

        print (approver_emails)

        context = {

        }

        # send_mail()

        activity_log = ActivityLog.objects.create(
            user=leaveRequest.requested_by,
            type=f'leaverequest_creation_{leaveRequest.id}',
            text=f"{leaveRequest.requested_by.first_name} {leaveRequest.requested_by.last_name} sent a leave request"
        )

        leaveRequest.activity.add(activity_log)

        type = "leaverequest_creation_" + str(leaveRequest.id)

        type = activity_log.type
        subject = type.split("_")[0]
        action = type.split("_")[1]
        id = type.split("_")[2]

        users = inclusion_matrix(
            email=activity_log.user.email,
            User_model=User,
            role=activity_log.user.role,
            department=activity_log.user.department,
            subject=subject,
            action=action,
            id=id
        )

        print (users)

        context = {
            'id': f'{id[:3]}',
            'title': leaveRequest.reason,
            'description': leaveRequest.notes,
            'date': leaveRequest.created_at
        }

        send_mail(
                subject=f"New Leave Request",
                to_email=list(users),
                context=context,
                type="leaverequest",
                action="creation"
        )

        return Response(
            self.get_serializer(leaveRequest).data,
            status=status.HTTP_201_CREATED
        )

class FacilityRequestViewSet(viewsets.ModelViewSet):
    queryset = FacilityRequest.objects.all()
    serializer_class = FacilityRequestSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'type']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        facilityRequest = serializer.save()

        activity_log = ActivityLog.objects.create(
            user=facilityRequest.requested_by,
            type=f'facilityrequest_creation_{facilityRequest.id}',
            text=f"{facilityRequest.requested_by.first_name} {facilityRequest.requested_by.last_name} sent a facility request"
        )

        facilityRequest.activity.add(activity_log)

        type = "facilityrequest_creation_" + str(facilityRequest.id)

        type = activity_log.type
        subject = type.split("_")[0]
        action = type.split("_")[1]
        id = type.split("_")[2]

        users = inclusion_matrix(
            email=activity_log.user.email,
            User_model=User,
            role=activity_log.user.role,
            department=activity_log.user.department,
            subject=subject,
            action=action,
            id=id
        )

        context = {
            'id': f'{id[:3]}',
            'title': facilityRequest.location,
            'description': facilityRequest.description,
            'date': facilityRequest.created_at
        }

        send_mail(
                subject=f"New Facility Request",
                to_email=list(users),
                context=context,
                type="facilityrequest",
                action="creation"
        )

        return Response(
            self.get_serializer(facilityRequest).data,
            status=status.HTTP_201_CREATED
        )

class ProcurementRequestViewSet(viewsets.ModelViewSet):
    queryset = ProcurementRequest.objects.all()
    serializer_class = ProcurementRequestSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'type']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        procurementRequest = serializer.save()

        approval_info, levels = approval_matrix(
            "procurementrequest",
            procurementRequest.requester.role,
            procurementRequest.requester.department
        )

        approval_info = attach_approvers_to_approval_info(
            approval_info=approval_info,
            requester=procurementRequest.requester,
            User_model=User
            )

        procurementRequest.approval_info = approval_info
        procurementRequest.save(update_fields=["approval_info"])

        approver_emails = extract_approval_emails(approval_info)

        print (approver_emails)

        context = {

        }

        # send_mail()

        activity_log = ActivityLog.objects.create(
            user=procurementRequest.requester,
            type=f'procurementrequest_creation_{procurementRequest.id}',
            text=f"{procurementRequest.requester.first_name} {procurementRequest.requester.last_name} sent a procurement request"
        )

        procurementRequest.activity.add(activity_log)

        type = "procurementrequest_creation_" + str(procurementRequest.id)

        type = activity_log.type
        subject = type.split("_")[0]
        action = type.split("_")[1]
        id = type.split("_")[2]

        users = inclusion_matrix(
            email=activity_log.user.email,
            User_model=User,
            role=activity_log.user.role,
            department=activity_log.user.department,
            subject=subject,
            action=action,
            id=id
        )

        context = {
            'id': f'{id[:3]}',
            'title': procurementRequest.center_code,
            'description': procurementRequest.justification,
            'date': procurementRequest.created_at
        }

        send_mail(
                subject=f"New procurement Request",
                to_email=list(users),
                context=context,
                type="procurementrequest",
                action="creation"
        )

        return Response(
            self.get_serializer(procurementRequest).data,
            status=status.HTTP_201_CREATED
        )       