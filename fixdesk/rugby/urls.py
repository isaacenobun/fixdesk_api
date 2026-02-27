from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, IssuesViewSet, MilestoneViewSet, CommentsViewSet, PaymentViewSet, DepartmentsViewSet, ActivityLogViewSet, LeaveRequestViewSet, FacilityRequestViewSet, ProcurementRequestViewSet, Comments_RequestsViewSet, TasksViewSet, microsoft_login
    )

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'issues', IssuesViewSet, basename='issue')
router.register(r'milestones', MilestoneViewSet, basename='milestone')
router.register(r'comments', CommentsViewSet, basename='comment')
router.register(r'comments-requests', Comments_RequestsViewSet, basename='comment_request')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'departments', DepartmentsViewSet, basename='department')
router.register(r'activity-logs', ActivityLogViewSet, basename='activity_log')
router.register(r'leave-requests', LeaveRequestViewSet, basename='leave_request')
router.register(r'facility-requests', FacilityRequestViewSet, basename='facility_request')
router.register(r'procurement-requests', ProcurementRequestViewSet, basename='procurement_request')
router.register(r'tasks', TasksViewSet, basename='task')

urlpatterns = [
    path('', include(router.urls)),
    path("auth/microsoft/", microsoft_login, name="microsoft_login"),
]