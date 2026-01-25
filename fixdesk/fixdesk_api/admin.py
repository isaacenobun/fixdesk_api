from django.contrib import admin
from .models import User, Issues, Conversations, Tenant
from .middleware import get_current_tenant

class TenantAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        tenant = get_current_tenant()
        if tenant:
            return qs.filter(tenant=tenant)
        return qs

    def save_model(self, request, obj, form, change):
        tenant = get_current_tenant()
        if tenant and hasattr(obj, 'tenant'):
            obj.tenant = tenant
        super().save_model(request, obj, form, change)

class UserAdmin(TenantAdmin):
    pass

class IssuesAdmin(TenantAdmin):
    pass

class ConversationsAdmin(TenantAdmin):
    pass

# Register your models here.
admin.site.register(Tenant)  # Perhaps only for superusers
admin.site.register(User, UserAdmin)
admin.site.register(Issues, IssuesAdmin)
admin.site.register(Conversations, ConversationsAdmin)