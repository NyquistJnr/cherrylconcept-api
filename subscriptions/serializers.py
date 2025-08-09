from rest_framework import serializers
from .models import Subscription

class SubscriptionSerializer(serializers.ModelSerializer):
    """
    Serializer for the Subscription model.
    """
    class Meta:
        model = Subscription
        fields = ['id', 'email', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_email(self, value):
        """
        Check if the email is already subscribed.
        """
        if Subscription.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email address is already subscribed.")
        return value
