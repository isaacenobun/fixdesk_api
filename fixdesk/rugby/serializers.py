from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model

User = get_user_model()

from .models import Issues, Payment, Tasks, Comments, Departments, ActivityLog, Issues, Milestone, Comments, LeaveRequest, FacilityRequest, ProcurementRequest, Comments_Requests

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

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'amount', 'payment_date', 'status']

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

class DepartmentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departments
        fields = ['id', 'name']

class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = ['id', 'user', 'type', 'text', 'timestamp']

class IssuesSerializer(serializers.ModelSerializer):
    comments = serializers.SerializerMethodField()

    class Meta:
        model = Issues
        fields = ['id', 'title', 'description', 'priority', 'status', 'created_at', 'type', 'category', 'attachment_key', 'reported_by', 'assigned_to', 'resolved_on', 'comments', 'activity']

    def get_comments(self, obj):
        qs = obj.rugby_comments.all().order_by('timestamp')
        return CommentsSerializer(qs, many=True).data
    
class MilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Milestone
        fields = ['id', 'title', 'status', 'due_date']
    
class TasksSerializer(serializers.ModelSerializer):
    comments = serializers.SerializerMethodField()
    activities = serializers.SerializerMethodField()

    class Meta:
        model = Tasks
        fields = ['id', 'title', 'description', 'priority', 'status', 'created_at', 'assigned_by', 'assigned_to', 'due_date', 'milestones', 'comments', 'activities']

    def get_comments(self, obj):
        qs = obj.rugby_comments.all().order_by('timestamp')
        return CommentsSerializer(qs, many=True).data
    
    def get_activities(self, obj):
        qs = obj.activity.all().order_by('timestamp')
        return ActivityLogSerializer(qs, many=True).data

class CommentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comments
        fields = ['id', 'case', 'message', 'commenter', 'mentioned_users', 'timestamp']

class LeaveRequestSerializer(serializers.ModelSerializer):
    comments = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = ['id', 'type', 'status', 'created_at', 'activity', 'start_date', 'end_date', 'reason', 'requested_by', 'notes', 'approval_info', 'comments']

    def get_comments(self, obj):
        qs = obj.rugby_comments.all().order_by('timestamp')
        return Comments_RequestsSerializer(qs, many=True).data

class FacilityRequestSerializer(serializers.ModelSerializer):
    comments = serializers.SerializerMethodField()

    class Meta:
        model = FacilityRequest
        fields = ['id', 'type', 'status', 'created_at', 'activity', 'location', 'priority', 'description', 'attachment_key', 'requested_by', 'assigned_to', 'comments']

    def get_comments(self, obj):
        qs = obj.rugby_comments.all().order_by('timestamp')
        return Comments_RequestsSerializer(qs, many=True).data

class ProcurementRequestSerializer(serializers.ModelSerializer):
    comments = serializers.SerializerMethodField()

    class Meta:
        model = ProcurementRequest
        fields = ['id', 'type', 'status', 'created_at', 'activity', 'requester', 'center_code', 'items', 'cost', 'justification', 'attachment_key', 'approval_info', 'comments']

    def get_comments(self, obj):
        qs = obj.rugby_comments.all().order_by('timestamp')
        return Comments_RequestsSerializer(qs, many=True).data
    
class Comments_RequestsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comments_Requests
        fields = ['id', 'request', 'message', 'commenter', 'mentioned_users', 'timestamp']