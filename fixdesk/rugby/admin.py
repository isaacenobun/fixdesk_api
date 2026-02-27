from django.contrib import admin
from .models import Issues, Payment, Tasks, Comments, Departments, ActivityLog, Milestone, LeaveRequest, FacilityRequest, ProcurementRequest, Comments_Requests

# Register your models here.
admin.site.register(Issues)
admin.site.register(Payment)
admin.site.register(Tasks)
admin.site.register(Comments)
admin.site.register(Departments)
admin.site.register(ActivityLog)
admin.site.register(Milestone)
admin.site.register(LeaveRequest)
admin.site.register(FacilityRequest)
admin.site.register(ProcurementRequest)
admin.site.register(Comments_Requests)