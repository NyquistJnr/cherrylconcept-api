from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import Subscription
from .serializers import SubscriptionSerializer

class IsAdminOrAllowCreate(permissions.BasePermission):
    """
    Custom permission:
    - Allows anyone to create (POST).
    - Allows only admin users for all other actions (GET, PUT, DELETE).
    """
    def has_permission(self, request, view):
        # Allow any user (authenticated or not) to create a subscription
        if view.action == 'create':
            return True
        # For all other actions, only allow admin users
        return request.user and request.user.is_staff

class SubscriptionViewSet(viewsets.ModelViewSet):
    """
    A ViewSet for managing email subscriptions.
    - POST (Create): Anyone can subscribe.
    - GET (List/Retrieve), PUT/PATCH (Update), DELETE (Destroy): Admin only.
    """
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAdminOrAllowCreate]

    def create(self, request, *args, **kwargs):
        """
        Custom create method to provide a clear success message on subscription.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {'message': 'Thank you for subscribing!', 'data': serializer.data},
            status=status.HTTP_201_CREATED,
            headers=headers
        )
