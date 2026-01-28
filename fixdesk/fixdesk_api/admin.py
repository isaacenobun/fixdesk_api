from django.contrib import admin
from .models import User, Issues, Conversations, VerificationCode

# Register your models here.
admin.site.register(User)
admin.site.register(Issues)
admin.site.register(Conversations)
admin.site.register(VerificationCode)