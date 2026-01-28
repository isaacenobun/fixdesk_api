from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.views import View
from django.db import transaction
from django.db.models import F

from decimal import Decimal

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.conf import settings
import requests
import json
import hashlib
import hmac

from .serializers import CreateCustomerSerializer ,PaymentLinkSerializer, CardAuthorizationSerializer, ChargeAuthorizationSerializer

from fixdesk_api.models import Organization, Payment, Webhook, Subscription, Authorizations

from datetime import datetime, timedelta

headers = {
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json",
            }

@method_decorator(csrf_exempt, name="dispatch")
class PaystackWebhookAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        # --- Verify signature ---
        paystack_signature = request.headers.get("x-paystack-signature")
        computed_signature = hmac.new(
            key=settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
            msg=request.body,
            digestmod=hashlib.sha512
        ).hexdigest()

        if paystack_signature != computed_signature:
            return JsonResponse({"error": "Invalid signature"}, status=400)

        try:
            event = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        event_type = event.get("event")
        data = event.get("data", {})
        metadata = data.get("metadata", {})
        authorization = data.get("authorization", {})

        # --- Handle different event types ---
        if event_type == "charge.success":
            
            if metadata.get("type") == "one_time":
                org_id = metadata.get("organization")
                org = Organization.objects.get(id=org_id)

                Payment.objects.create(
                    Organization = org,
                    amount = Decimal(data.get("amount", 0) / 100),
                    status = 'success',
                    reference = data.get("reference")
                )
                
                Webhook.objects.create(
                    organization = org,
                    event = event_type,
                    payload = data,
                    status = 'success'
                )
                    
                return JsonResponse({"status": "success"}, status=200)
            
            elif metadata.get("type") == "subscription":
                org_id = metadata.get("organization")
                org = Organization.objects.get(id=org_id)
                subscription_id = metadata.get("subscription_id")
                subscription = Subscription.objects.get(id=subscription_id)

                Payment.objects.create(
                    organization = org,
                    subscription = subscription,
                    amount = Decimal(data.get("amount", 0) / 100),
                    status = 'success',
                    reference = data.get("reference")
                )

                subscription.status = 'active'
                subscription.current_period_start = datetime.now()
                if subscription.plan == 'monthly':
                    subscription.current_period_end = datetime.now() + timedelta(months=1)
                elif subscription.plan == 'yearly':
                    subscription.current_period_end = datetime.now() + timedelta(months=12)
                subscription.save()
                
                Webhook.objects.create(
                    organization = org,
                    event = event_type,
                    payload = data,
                    status = 'success'
                )
                    
                return JsonResponse({"status": "success"}, status=200)
            
            # elif metadata.get("type") == "charge_authorization":
            
            elif metadata.get("type") == "card_authorization":

                Authorizations.objects.create(
                    organization = Organization.objects.get(id=metadata.get("organization")),
                    url = authorization.get("authorization_url"),
                    access_code = data.get("access_code"),
                    reference = data.get("reference"),
                    status = 'active'
                )

                Webhook.objects.create(
                    organization = Organization.objects.get(id=metadata.get("organization")),
                    event = "card_authorization_success",
                    payload = data,
                    status = 'success'
                )
        
        else:
            # Unhandled event type
            pass

        return JsonResponse({"status": "success"}, status=200)