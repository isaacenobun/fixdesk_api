from django.db import models
from django.contrib.auth.models import BaseUserManager
from django.conf import settings

import uuid

from .fields import EncryptedTextField
    
class UUIDModel(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    class Meta:
        abstract = True

class UserManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, email):
        # Try default DB
        try:
            return self.using("default").get(email=email)
        except self.model.DoesNotExist:
            pass

        # Try rugby DB
        try:
            return self.using("rugby").get(email=email)
        except self.model.DoesNotExist:
            raise

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username=None, email=None, password=None, **extra_fields):
        # accept `username` for compatibility with Django management commands
        email = email or username
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, username=None, email=None, password=None, **extra_fields):
        email = email or username
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)
     
class Payment(UUIDModel):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.CharField(max_length=20, default='pending', db_index=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"{self.amount}"
    
class Departments(UUIDModel):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
    
class ActivityLog(UUIDModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rugby_activity_logs')
    type = models.CharField(max_length=100) 
    # "subject_action_id"

    # "issue_creation_id", "issue_status_id", "issue_assigned_id", "issue_comment_id"

    # "task_creation_id", "task_status_id", "task_assigned_id", "task_comment_id"

    # "facilityrequest_creation_id", "facilityrequest_status_id", "facilityrequest_assigned_id", "facilityrequest_comment_id"

    # "procurementrequest_creation_id", "procurementrequest_status_id", "procurementrequest_assigned_id", "procurementrequest_comment_id"

    # "leaverequest_creation_id", "leaverequest_status_id", "leaverequest_assigned_id", "leaverequest_comment_id"

    text = models.CharField(max_length=200)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.text[:25]}..."
    
class Issues_Tasks(UUIDModel):
    title = models.CharField(max_length=100)
    description = models.TextField()
    priority = models.CharField(max_length=20, default='low', db_index=True)
    status = models.CharField(max_length=20, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    activity = models.ManyToManyField(ActivityLog, related_name='rugby_issues_tasks', blank=True)

class Issues(Issues_Tasks):
    type = models.CharField(max_length=20, db_index=True)
    category = models.CharField(max_length=50, db_index=True)
    attachment = models.CharField(max_length=100, blank=True, null=True)
    attachment_key = models.CharField(max_length=100, blank=True, null=True)
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rugby_reported_issues')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='rugby_assigned_issues', blank=True, null=True, on_delete=models.SET_NULL)
    resolved_on = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
    
class Milestone(UUIDModel):
    title = models.CharField(max_length=100)
    due_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default='unchecked', db_index=True)
    completed_on = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-due_date']
        
    def __str__(self):
        return self.title
    
class Tasks(Issues_Tasks):
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rugby_created_tasks', null=True, blank=True)
    assigned_to = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='rugby_tasks')
    due_date = models.DateTimeField(null=True, blank=True)
    milestones = models.ManyToManyField(Milestone, related_name='rugby_tasks', blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
    
class Comments(UUIDModel):
    case = models.ForeignKey('Issues_Tasks', on_delete=models.CASCADE, related_name='rugby_comments', db_index=True)
    message = models.TextField()
    commenter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rugby_case_comments')
    mentioned_users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='rugby_case_mentioned_in_comments', blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.message[:25]}..."
    
class Requests(UUIDModel):
    type = models.CharField(max_length=20, db_index=True)
    activity = models.ManyToManyField(ActivityLog, related_name='rugby_requests', blank=True)
    status = models.CharField(max_length=20, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

class LeaveRequest(Requests):
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rugby_leave_requests')
    notes = models.TextField(blank=True, null=True)
    approval_info = models.JSONField(blank=True, null=True)

class FacilityRequest(Requests):
    location = models.CharField(max_length=100)
    priority = models.CharField(max_length=20, default='low', db_index=True)
    description = models.TextField()
    attachment = models.CharField(max_length=100, blank=True, null=True)
    attachment_key = models.CharField(max_length=100, blank=True, null=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rugby_facility_requests')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='rugby_assigned_facility_requests', blank=True, null=True, on_delete=models.SET_NULL)

class ProcurementRequest(Requests):
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rugby_procurement_requests')
    center_code = models.CharField(max_length=50, db_index=True)
    items = models.JSONField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    justification = models.TextField()
    attachment = models.CharField(max_length=100, blank=True, null=True)
    attachment_key = models.CharField(max_length=100, blank=True, null=True)
    approval_info = models.JSONField(blank=True, null=True)

class Comments_Requests(UUIDModel):
    request = models.ForeignKey('Requests', on_delete=models.CASCADE, related_name='rugby_comments', db_index=True)
    message = models.TextField()
    commenter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rugby_request_comments')
    mentioned_users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='rugby_requests_mentioned_in_comments', blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.message[:25]}..."

# --------------------------------------------------------------------------------------------------------
# Encryption

class Keyring(UUIDModel):
    # Store wrapped DEK for each version
    version = models.PositiveIntegerField(unique=True)
    dek_wrapped = models.BinaryField()
    dek_nonce = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]

class SecretRecord(UUIDModel):
    ciphertext = models.BinaryField()
    nonce = models.BinaryField()
    key_version = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)