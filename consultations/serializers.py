from rest_framework import serializers
from .models import Consultation

class ConsultationSerializer(serializers.ModelSerializer):
    """
    Serializer for the Consultation model.
    """
    # Make the user field read-only because we set it automatically in the view.
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Consultation
        fields = [
            'id', 
            'user', 
            'full_name', 
            'email', 
            'message', 
            'consultation_time', 
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        """
        If the user is authenticated, we use their details by default.
        This prevents a logged-in user from booking for someone else via the API.
        """
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            # Pre-fill name and email from the logged-in user's profile
            attrs['full_name'] = request.user.full_name
            attrs['email'] = request.user.email
        
        # For anonymous users, full_name and email are required from the payload.
        # This check is implicitly handled by the model field definitions.

        return attrs
