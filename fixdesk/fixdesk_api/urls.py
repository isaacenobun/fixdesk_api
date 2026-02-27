from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, IssuesViewSet, ConversationsViewSet, VerificationCodeViewSet, OrganizationViewSet, SubscriptionViewSet, PaymentViewSet, AuthorizationsViewSet, WebhookViewSet, TasksViewSet, CommentsViewSet, InvitationViewSet
    )

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'issues', IssuesViewSet)
router.register(r'messages', ConversationsViewSet)
router.register(r'verify', VerificationCodeViewSet)
router.register(r'organizations', OrganizationViewSet)
router.register(r'subscriptions', SubscriptionViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'authorizations', AuthorizationsViewSet)
router.register(r'webhooks', WebhookViewSet)
router.register(r'tasks', TasksViewSet)
router.register(r'comments', CommentsViewSet)
router.register(r'invitations', InvitationViewSet)

urlpatterns = [
    path('', include(router.urls)),
]