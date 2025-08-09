from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import Consultation
from .serializers import ConsultationSerializer
from .pagination import ConsultationPagination 

class IsAdminOrAllowAny(permissions.BasePermission):
    """
    Custom permission to only allow admin users to list, retrieve, update, or delete,
    but allow anyone to create a new object.
    """
    def has_permission(self, request, view):
        if view.action == 'create':
            return True
        return request.user and request.user.is_staff

class ConsultationViewSet(viewsets.ModelViewSet):
    """
    A ViewSet for viewing and editing consultation instances.
    Provides full CRUD functionality with custom pagination.
    """
    queryset = Consultation.objects.all()
    serializer_class = ConsultationSerializer
    permission_classes = [IsAdminOrAllowAny]
    pagination_class = ConsultationPagination  # <-- Add this line to enable custom pagination

    def perform_create(self, serializer):
        """
        If the user is authenticated, associate the consultation with their account.
        """
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()

    def create(self, request, *args, **kwargs):
        """
        Custom create method to provide a clear success message.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {'message': 'Consultation booked successfully.', 'data': serializer.data}, 
            status=status.HTTP_201_CREATED, 
            headers=headers
        )