from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

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
    
class Subscription(UUIDModel):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name='subscriptions', db_index=True)
    plan = models.CharField(max_length=50, default='monthly', db_index=True)
    status = models.CharField(max_length=20, default='active', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.organization
    
class Payment(UUIDModel):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name='payments', db_index=True)
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, related_name='payments', blank=True, null=True, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.CharField(max_length=20, default='pending', db_index=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"{self.organization} - {self.amount}"
    
class Authorizations(UUIDModel):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="authorizations")
    url = models.URLField(max_length=200, null=True, blank=True)
    access_code = models.CharField(max_length=100, null=True, blank=True)
    reference = models.CharField(max_length=100, null=True, blank=True)
    auth_type = models.CharField(max_length=20, default='card')
    status = models.CharField(max_length=10, default="inactive")
    authorization_code = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return str(self.user_id)
    
class Webhook(UUIDModel):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="webhooks", db_index=True)
    event = models.CharField(max_length=100)
    payload = models.JSONField(blank=True, null=True)
    status = models.CharField(max_length=20, default='pending', db_index=True)
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    def __str__(self):
        return self.event
    
class Organization(UUIDModel):
    name = EncryptedTextField()
    subdomain = models.CharField(max_length=100, unique=True, null=True, blank=True)
    allowed_email_domain = models.CharField(max_length=255, null=True, blank=True
    )
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    departments = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name
    
class User(AbstractUser):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='users', db_index=True, null=True, blank=True)
    username = None
    objects = UserManager()
    first_name = EncryptedTextField(null=True, blank=True)
    last_name = EncryptedTextField(null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    role = models.CharField(max_length=10, default='staff', db_index=True)
    department = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name="staff_user_groups",
        blank=True,
        help_text="The groups this user belongs to."
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name="staff_user_permissions",
        blank=True,
        help_text="Specific permissions for this user."
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.email
    
class Category(UUIDModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='categories', db_index=True)
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    department = models.CharField(max_length=50, null=True, blank=True)
    color = models.CharField(max_length=7, default='#000000')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name
    
class Rules(UUIDModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='rules', db_index=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    conditions = models.JSONField()
    action = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

class Issues(UUIDModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='issues', db_index=True)
    title = models.CharField(max_length=100)
    description = models.TextField()
    priority = models.CharField(max_length=20, default='low', db_index=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, related_name='issues', null=True, blank=True, db_index=True)
    status = models.CharField(max_length=20, default='pending', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reported_issues')
    assigned_to = models.ForeignKey(User, related_name='assigned_issues', blank=True, null=True, on_delete=models.SET_NULL)
    resolved_on = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class Conversations(UUIDModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='conversations', db_index=True)
    issue = models.ForeignKey('Issues', on_delete=models.CASCADE, related_name='conversations', db_index=True)
    message = models.TextField()
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    mentioned_users = models.ManyToManyField(User, related_name='mentioned_in_messages', blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.message[:25]}..."
    
class Tasks(UUIDModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='tasks', db_index=True)
    title = models.CharField(max_length=100)
    description = models.TextField()
    priority = models.CharField(max_length=20, default='low', db_index=True)
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tasks', null=True, blank=True)
    assigned_to = models.ManyToManyField(User, related_name='tasks')
    status = models.CharField(max_length=20, default='pending', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    due_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
    
class Comments(UUIDModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='comments', db_index=True)
    task = models.ForeignKey('Tasks', on_delete=models.CASCADE, related_name='comments', db_index=True)
    message = models.TextField()
    commenter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    mentioned_users = models.ManyToManyField(User, related_name='mentioned_in_comments', blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.message[:25]}..."

class VerificationCode(UUIDModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="verification_codes", null=True, blank=True, db_index=True)
    code = models.CharField(max_length=6, unique=True, editable=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code}"

class Invitation(UUIDModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='invitations', db_index=True)
    email = models.EmailField(db_index=True)
    role = models.CharField(max_length=10, default='staff', db_index=True)
    department = models.CharField(max_length=50, null=True, blank=True)
    token = models.CharField(max_length=100, unique=True, editable=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    accepted = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Invitation for {self.email}"

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