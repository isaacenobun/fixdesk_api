from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate

from .models import User, Issues, Conversations, VerificationCode, Organization, Subscription, Payment, Authorizations, Webhook, Tasks, Comments, Invitation

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        credentials = {
            "email": attrs.get("email"),
            "password": attrs.get("password"),
        }
        user = authenticate(**credentials)
        if user and user.is_active:
            data = super().validate(attrs)
            return data
        raise serializers.ValidationError("Invalid email or password")
    
class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ['id', 'type', 'created_at']

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'organization', 'subscription', 'amount', 'payment_date', 'status']

class AuthorizationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Authorizations
        fields = ['id', 'organization', 'url', 'access_code', 'reference', 'auth_type', 'status', 'authorization_code', 'created_at']

class WebhookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Webhook
        fields = ['id', 'organization', 'event', 'payload', 'status', 'received_at']

class OrganizationSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True)
    class Meta:
        model = Organization
        fields = ['id', 'name', 'subdomain', 'allowed_email_domain', 'slug', 'created_at']

class UserSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=False, allow_null=True)
    last_name = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ['id', 'organization', 'first_name', 'last_name', 'email', 'role', 'department', 'created_at', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        instance = self.Meta.model(**validated_data)
        
        instance.is_active = True
        if password is not None:
            instance.set_password(password)
        instance.save()
        return instance

class IssuesSerializer(serializers.ModelSerializer):
    conversations = serializers.SerializerMethodField()

    class Meta:
        model = Issues
        fields = ['id', 'organization', 'title', 'description', 'priority', 'status', 'created_at', 'reported_by', 'resolved_on', 'conversations']

    def get_conversations(self, obj):
        qs = obj.conversations.all().order_by('timestamp')
        return ConversationsSerializer(qs, many=True).data

class ConversationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversations
        fields = ['id', 'issue', 'message', 'sender', 'mentioned_users', 'timestamp']

class TasksSerializer(serializers.ModelSerializer):
    comments = serializers.SerializerMethodField()

    class Meta:
        model = Tasks
        fields = ['id', 'organization', 'title', 'description', 'priority', 'assigned_by', 'assigned_to', 'status', 'due_date', 'created_at', 'comments']

    def get_comments(self, obj):
        qs = obj.comments.all().order_by('timestamp')
        return CommentsSerializer(qs, many=True).data

class CommentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comments
        fields = ['id', 'organization', 'task', 'message', 'commenter', 'mentioned_users', 'timestamp']

class VerificationCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationCode
        fields = ['id', 'used', 'user', 'code', 'created_at']

class InvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = ['id', 'organization', 'email', 'role', 'department', 'token', 'created_at', 'accepted']