from django.contrib import admin
from .models import User, Issues, Conversations, VerificationCode, Organization, Subscription, Payment, Authorizations, Webhook, Tasks, Comments, Invitation

# Register your models here.
admin.site.register(Organization)
admin.site.register(User)
admin.site.register(Issues)
admin.site.register(Tasks)
admin.site.register(Conversations)
admin.site.register(VerificationCode)
admin.site.register(Subscription)
admin.site.register(Payment)
admin.site.register(Authorizations)
admin.site.register(Webhook)
admin.site.register(Comments)
admin.site.register(Invitation)