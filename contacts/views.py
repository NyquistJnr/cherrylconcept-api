from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import ContactMessage
from .serializers import ContactMessageSerializer

class IsAdminOrAllowCreate(permissions.BasePermission):
    """
    Custom permission:
    - Allows anyone to create (POST) a contact message.
    - Allows only admin users for all other actions (GET, PUT, DELETE).
    """
    def has_permission(self, request, view):
        if view.action == 'create':
            return True
        return request.user and request.user.is_staff

class ContactMessageViewSet(viewsets.ModelViewSet):
    """
    A ViewSet for managing contact form submissions.
    - POST (Create): Anyone can send a message.
    - GET (List/Retrieve), PUT/PATCH (Update), DELETE (Destroy): Admin only.
    """
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [IsAdminOrAllowCreate]

    def create(self, request, *args, **kwargs):
        """
        Custom create method to provide a clear success message.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {'message': 'Your message has been sent successfully! We will get back to you shortly.', 'data': serializer.data},
            status=status.HTTP_201_CREATED,
            headers=headers
        )
