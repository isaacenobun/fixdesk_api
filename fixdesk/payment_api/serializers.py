from rest_framework import serializers

class CreateCustomerSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    phone_number = serializers.CharField(required=False)

class PaymentLinkSerializer(serializers.Serializer):
    email = serializers.EmailField()
    amount = serializers.IntegerField(min_value=1)
    user = serializers.CharField(required=False)
    type = serializers.CharField(required=False)
    reference = serializers.CharField(required=False)
    
class ChargeAuthorizationSerializer(serializers.Serializer):
    webhook_id = serializers.CharField()
    charge = serializers.IntegerField()
    driver_wallet_id = serializers.CharField()
    driver_wallet_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    email = serializers.EmailField()
    amount = serializers.IntegerField(min_value=1)
    
class CardAuthorizationSerializer(serializers.Serializer):
    authorization_id = serializers.CharField()
    email = serializers.EmailField()
    amount = serializers.IntegerField(min_value=1)