from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from dotenv import load_dotenv
load_dotenv()

from .tasks import send_mail

import random
import string

from .models import User, Issues, Conversations, VerificationCode, Organization, Subscription, Payment, Authorizations, Webhook, Tasks, Comments, Invitation

from .serializers import MyTokenObtainPairSerializer, UserSerializer, IssuesSerializer, ConversationsSerializer, VerificationCodeSerializer, OrganizationSerializer, SubscriptionSerializer, PaymentSerializer, AuthorizationsSerializer, WebhookSerializer, TasksSerializer, CommentsSerializer, InvitationSerializer

class MyTokenObtainPairView(TokenObtainPairView):
    """
    Custom TokenObtainPairView using MyTokenObtainPairSerializer.
    """
    serializer_class = MyTokenObtainPairSerializer

class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['type']

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related('organization', 'subscription')
    serializer_class = PaymentSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['organization', 'subscription', 'status']

class AuthorizationsViewSet(viewsets.ModelViewSet):
    queryset = Authorizations.objects.select_related('organization')
    serializer_class = AuthorizationsSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['organization', 'status', 'auth_type']

class WebhookViewSet(viewsets.ModelViewSet):
    queryset = Webhook.objects.select_related('organization')
    serializer_class = WebhookSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['organization', 'event', 'status']

class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['slug']

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['email']

class IssuesViewSet(viewsets.ModelViewSet):
    queryset = Issues.objects.select_related('organization', 'reported_by')
    serializer_class = IssuesSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'reported_by']

    def partial_update(self, request, *args, **kwargs):
        issue = self.get_object()
        new_status = request.data.get('status')

        # Handle status change independently
        if new_status and new_status != issue.status:
            issue.status = new_status
            issue.save(update_fields=['status'])

            context = {
                'organization': issue.organization.slug,
                'ticket_id': f'TK-{issue.id[:3]}',
                'title': issue.title,
                'description': issue.description,
                'date': issue.created_at,
                'status': new_status
            }

            status_messages = {
                'completed': (f'Issue TK-{issue.id[:3]} Resolved', 'issue_status'),
                'pending': (f'Issue TK-{issue.id[:3]} Reopened', 'issue_status'),
            }

            if new_status in status_messages:
                subject, mail_type = status_messages[new_status]
                send_mail.apply_async(
                    kwargs={
                        'subject': subject,
                        'to_email': issue.reported_by.email,
                        'context': context,
                        'type': mail_type
                    }
                )

        # Handle other fields separately
        data = {k: v for k, v in request.data.items() if k != 'status'}
        if data:
            serializer = self.get_serializer(issue, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response({'status': 'updated'}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        response = super().create(request, *args, **kwargs)
        issue = Issues.objects.select_related('organization', 'reported_by').get(id=response.data['id'])
        
        context = {
            'organization': issue.organization.slug,
            'ticket_id': 'TK-'+str(issue.id)[:3],
            'title': issue.title,
            'description': issue.description,
            'reported_by': issue.reported_by.first_name + ' ' + issue.reported_by.last_name,
            'date': issue.created_at,
        }

        # To Admins - Use values_list to avoid loading full User objects
        admin_emails = list(User.objects.filter(
            organization=issue.organization, 
            role='admin'
        ).values_list('email', flat=True))
        
        send_mail.apply_async(
            kwargs={
                'subject': "New Issue Reported",
                'to_email': admin_emails,
                'context': context,
                'type': "admin"
            }
        )

        # To User
        send_mail.apply_async(
            kwargs={
                'subject': "Issue Reported Successfully",
                'to_email': issue.reported_by.email,
                'context': context,
                'type': "user"
            }
        )

        return response

class ConversationsViewSet(viewsets.ModelViewSet):
    queryset = Conversations.objects.select_related('organization', 'issue', 'sender').prefetch_related('mentioned_users')
    serializer_class = ConversationsSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['issue']

    def create(self, request, *args, **kwargs):
        message = request.data.get('message')
        issue = Issues.objects.select_related('organization', 'reported_by').get(id=request.data.get('issue'))
        sender = User.objects.get(id=request.data.get('sender'))

        if sender.role == 'admin':
            context = {
                'organization': issue.organization.slug,
                'message': message,
                'ticket_id': 'TK-'+str(issue.id)[:3],
                'sender': sender.first_name + ' ' + sender.last_name,
            }

            send_mail.apply_async(
                kwargs={
                    'subject': f"New Message on Issue (ID: {context.get('ticket_id')})",
                    'to_email': [issue.reported_by.email],
                    'context': context,
                    'type': "message"
                }
            )

            return super().create(request, *args, **kwargs)

        else:
            context = {
                'organization': issue.organization.slug,
                'message': message,
                'ticket_id': 'TK-'+str(issue.id)[:3],
                'sender': sender.first_name + ' ' + sender.last_name,
            }

            admin_emails = list(User.objects.filter(
                organization=issue.organization, 
                role='admin'
            ).values_list('email', flat=True))
            
            send_mail.apply_async(
                kwargs={
                    'subject': f"New Message on Issue (ID: {context.get('ticket_id')})",
                    'to_email': admin_emails,
                    'context': context,
                    'type': "message"
                }
            )
            return super().create(request, *args, **kwargs)
        
class TasksViewSet(viewsets.ModelViewSet):
    queryset = Tasks.objects.select_related('organization').prefetch_related('assigned_to')
    serializer_class = TasksSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'assigned_to']

    def partial_update(self, request, *args, **kwargs):
        task = self.get_object()
        new_status = request.data.get('status')
        id = request.data.get('id')

        # Handle status change independently
        if new_status and new_status != task.status:
            task.status = new_status
            task.save(update_fields=['status'])

        context = {
            'organization': task.organization.slug,
            'task_id': f'TSK-{id[:3]}',
            'title': task.title,
            'description': task.description,
            'due_date': task.due_date,
            'status': new_status
        }

        status_messages = {
            'completed': (f'{context.get("task_id")} Completed', 'task_status'),
            'pending': (f'Task {context.get("task_id")} Reopened', 'task_status'),
        }

        if new_status in status_messages:
            subject, mail_type = status_messages[new_status]
            for user in task.assigned_to.all():
                send_mail.apply_async(
                    kwargs={
                        'subject': subject,
                        'to_email': user.email,
                        'context': context,
                        'type': mail_type
                    }
                )

        # Handle other fields separately
        data = {k: v for k, v in request.data.items() if k != 'status'}
        if data:
            serializer = self.get_serializer(task, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response({'status': 'updated'}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        response = super().create(request, *args, **kwargs)
        task = Tasks.objects.select_related('organization', 'assigned_by').prefetch_related('assigned_to').get(id=response.data['id'])
        assigned_users = task.assigned_to.all()

        context = {
            'organization': task.organization.slug,
            'assigned_by': task.assigned_by.first_name + ' ' + task.assigned_by.last_name,
            'assigned_to': ', '.join([user.first_name + ' ' + user.last_name for user in assigned_users]),
            'task_id': 'TSK-'+str(task.id)[:3],
            'title': task.title,
            'description': task.description,
            'priority': task.priority,
            'due_date': task.due_date,
        }

        for user in assigned_users:
            send_mail.apply_async(
                kwargs={
                    'subject': "New Task Assigned",
                    'to_email': user.email,
                    'context': context,
                    'type': "task"
                }
            )

        return response

class CommentsViewSet(viewsets.ModelViewSet):
    queryset = Comments.objects.select_related('organization', 'task', 'commenter').prefetch_related('mentioned_users')
    serializer_class = CommentsSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['task', 'commenter']

    def create(self, request, *args, **kwargs):
        comment_text = request.data.get('message')
        task = Tasks.objects.select_related('organization').get(id=request.data.get('task'))
        commenter = User.objects.get(id=request.data.get('commenter'))

        context = {
            'organization': task.organization.slug,
            'comment': comment_text,
            'task_id': 'TSK-'+str(task.id)[:3],
            'commenter': commenter.first_name + ' ' + commenter.last_name,
        }

        all_users = set(task.assigned_to.values_list('id', flat=True)) | set(request.data.get('mentioned_users', []))
        all_users = User.objects.filter(id__in=all_users)
        for user in all_users:
            if user.id != commenter.id:
                send_mail.apply_async(
                    kwargs={
                        'subject': f"New Comment on Task (ID: {context.get('task_id')})",
                        'to_email': user.email,
                        'context': context,
                        'type': "comment"
                    }
                )

        return super().create(request, *args, **kwargs)

def generate_verification_code():
    """Generates a unique 5-digit code for VerificationCode."""
    import secrets
    length = 5
    characters = string.digits 
    max_attempts = 50
    attempts = 0
    
    while attempts < max_attempts:
        code = ''.join(secrets.choice(characters) for _ in range(length))
        if not VerificationCode.objects.filter(code=code).exists():
            return code
        attempts += 1

class VerificationCodeViewSet(viewsets.ModelViewSet):
    queryset = VerificationCode.objects.select_related('user')
    serializer_class = VerificationCodeSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['code']

    def create(self, request, *args, **kwargs):
        # Generate a unique verification code
        code = generate_verification_code()
        
        email = request.data.get('email', None)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = None

        context = {
            'organization': user.organization.slug if user else None,
            'verification_code': code
        }

        if user:
            send_mail.apply_async(
                kwargs={
                    'subject': "Reset your Helpdesk Password",
                    'to_email': user.email,
                    'context': context,
                    'type': "verify"
                }
            )
        else:
            send_mail.apply_async(
                kwargs={
                    'subject': "Activate your account",
                    'to_email': email,
                    'context': context,
                    'type': "activate"
                }
            )
        if user:
            verification_code = VerificationCode.objects.create(user=user, code=code)
        else:
            verification_code = VerificationCode.objects.create(code=code)
        serializer = self.get_serializer(verification_code)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
class InvitationViewSet(viewsets.ModelViewSet):
    queryset = Invitation.objects.select_related('organization')
    serializer_class = InvitationSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['email', 'organization']

    def create(self, request, *args, **kwargs):
        email = request.data.get('email')
        organization_id = request.data.get('organization')
        role = request.data.get('role', 'user')
        department = request.data.get('department', '')

        try:
            organization = Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist:
            return Response({'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)

        token = ''.join(random.choices(string.ascii_letters + string.digits, k=20))

        invitation = Invitation.objects.create(
            organization=organization,
            email=email,
            role=role,
            department=department,
            token=token
        )

        context = {
            'organization': organization.slug,
            'email': email,
            'role': role,
            'department': department,
            'token': token,
            "link": f"https://fixdesk.ng/activate?token={token}"
        }

        send_mail.apply_async(
            kwargs={
                'subject': f"Invitation to join {organization.name} on Helpdesk",
                'to_email': email,
                'context': context,
                'type': "activate"
            }
        )
        serializer = self.get_serializer(invitation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)