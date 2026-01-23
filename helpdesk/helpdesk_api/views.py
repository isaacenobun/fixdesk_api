import os
from django.shortcuts import render
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework import status

from django.template.loader import render_to_string

# SMTP
import smtplib, ssl
from email.message import EmailMessage

from dotenv import load_dotenv
load_dotenv()

import random
import string

from .models import User, Issues, Conversations, VerificationCode
from .serializers import MyTokenObtainPairSerializer, UserSerializer, IssuesSerializer, ConversationsSerializer, VerificationCodeSerializer

def send_mail(subject, to_email, context, type):
        port = 587
        smtp_server =os.getenv('SMTP_SERVER')
        username=os.getenv('EMAIL_USER')
        password =os.getenv('EMAIL_PASSWORD')
        
        if type == "admin":
            html_content = render_to_string('admin_notification.html', context)
        elif type == "user":
            html_content = render_to_string('user_notification.html', context)
        elif type == "verify":
            html_content = render_to_string('user_verification.html', context)
        elif type == "message":
            html_content = render_to_string('message_notification.html', context)

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = "helpdesk@creditreferencenigeria.net"
        msg['To'] = [to_email]
        msg.set_content(html_content, subtype='html')
        
        try:
            if port == 465:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
                    server.login(username, password)
                    server.send_message(msg)
            elif port == 587:
                with smtplib.SMTP(smtp_server, port) as server:
                    server.starttls()
                    server.login(username, password)
                    server.send_message(msg)
            else:
                print ("use 465 / 587 as port value")
                exit()
            return True
        except Exception as e:
            print (e)
            return False

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

class IssuesViewSet(viewsets.ModelViewSet):
    queryset = Issues.objects.all()
    serializer_class = IssuesSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'reported_by']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        response = super().create(request, *args, **kwargs)
        issue = Issues.objects.get(id=response.data['id'])
        
        context = {
            'ticket_id': 'CRC-'+str(issue.id),
            'title': issue.title,
            'description': issue.description,
            'reported_by': issue.reported_by.first_name + ' ' + issue.reported_by.last_name,
            'date': issue.created_at,
        }

        # To Admin
        if send_mail(
            subject="New Issue Reported",
            # to_email= technology.admin_email,
            to_email="isaac.enobun@crccreditbureau.net",
            context=context,
            type="admin"
        ):
            print("Admin notification sent successfully.")
        else:
            print("Failed to send admin notification.")

        # To User
        if send_mail(
            subject="Issue Reported Successfully",
            # to_email=issue.reported_by.email,
            to_email="isaac.enobun@crccreditbureau.net",
            context=context,
            type="user"
        ):
            print("User notification sent successfully.")
        else:
            print("Failed to send user notification.")

        return response

class ConversationsViewSet(viewsets.ModelViewSet):
    queryset = Conversations.objects.all()
    serializer_class = ConversationsSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['issue']

    def create(self, request, *args, **kwargs):
        message = request.data.get('message')
        issue = Issues.objects.get(id=request.data.get('issue'))
        sender = User.objects.get(id=request.data.get('sender'))

        if sender.role == 'admin':

            context = {
                'message': message,
                'ticket_id': 'CRC-'+str(issue.id),
                'sender': sender.first_name + ' ' + sender.last_name,
            }

            if send_mail(
                subject="New Message on Issue (ID: CRC-"+str(issue.id)+")",
                # to_email=issue.reported_by.email,
                to_email="isaac.enobun@crccreditbureau.net",
                context=context,
                type="message"
            ):
                print("Message notification sent successfully to user.")
            else:
                print("Failed to send message notification to user.")

            return super().create(request, *args, **kwargs)

        else:
            context = {
                'message': message,
                'ticket_id': 'CRC-'+str(issue.id),
                'sender': issue.reported_by.first_name + ' ' + issue.reported_by.last_name,
            }

            if send_mail(
                subject="New Message on Issue (ID: CRC-"+str(issue.id)+")",
                # to_email=technology.admin_email,
                to_email="isaac.enobun@crccreditbureau.net",
                context=context,
                type="message"
            ):
                print("Message notification sent successfully to admin.")
            else:
                print("Failed to send message notification to admin.")

            return super().create(request, *args, **kwargs)

def generate_verification_code():
    """Generates a unique 5-digit code for VerificationCode."""
    length = 5
    characters = string.digits 
    
    while True:
        code = ''.join(random.choice(characters) for _ in range(length))
        if not VerificationCode.objects.filter(code=code).exists():
            break
    return code

class VerificationCodeViewSet(viewsets.ModelViewSet):
    queryset = VerificationCode.objects.all()
    serializer_class = VerificationCodeSerializer
    http_method_names = ['get', 'post', 'put', 'patch']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['code']

    def create(self, request, *args, **kwargs):
        # Generate a unique verification code
        code = generate_verification_code()
        user = User.objects.get(id=request.data.get('user'))

        context = {
            'verification_code': code
        }

        if send_mail(
            subject="Reset your Helpdesk Password",
            # to_email=user.email,
            to_email="isaac.enobun@crccreditbureau.net",
            context=context,
            type="verify"
        ):
            print("Verification code sent successfully.")
        else:
            print("Failed to send verification code.")

        verification_code = VerificationCode.objects.create(user=user, code=code)
        serializer = self.get_serializer(verification_code)
        return Response(serializer.data, status=status.HTTP_201_CREATED)