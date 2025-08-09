from rest_framework import serializers
from .models import ContactMessage

class ContactMessageSerializer(serializers.ModelSerializer):
    """
    Serializer for the ContactMessage model.
    """
    class Meta:
        model = ContactMessage
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'department',
            'subject',
            'message',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
