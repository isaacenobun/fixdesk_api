import threading
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404

_thread_locals = threading.local()

def get_current_tenant():
    return getattr(_thread_locals, 'tenant', None)

def set_current_tenant(tenant):
    _thread_locals.tenant = tenant

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from .models import Tenant  # Import here to avoid circular import
        host = request.get_host().split(':')[0]  # Remove port if present
        subdomain = self.get_subdomain(host)
        
        if subdomain:
            try:
                tenant = Tenant.objects.get(slug=subdomain, is_active=True)
                set_current_tenant(tenant)
            except Tenant.DoesNotExist:
                raise Http404("Tenant not found")
        else:
            # For main domain or localhost, perhaps no tenant or default
            set_current_tenant(None)
        
        response = self.get_response(request)
        return response

    def get_subdomain(self, host):
        """
        Extract subdomain from host.
        Assumes domain is like subdomain.api.yoursaas.com
        """
        parts = host.split('.')
        if len(parts) >= 3 and parts[-2] + '.' + parts[-1] == 'api.yoursaas.com':
            return parts[0]
        return None