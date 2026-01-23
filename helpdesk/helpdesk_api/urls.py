from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, IssuesViewSet, ConversationsViewSet, VerificationCodeViewSet
    )

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'issues', IssuesViewSet)
router.register(r'messages', ConversationsViewSet)
router.register(r'verify', VerificationCodeViewSet)

urlpatterns = [
    path('', include(router.urls)),
]