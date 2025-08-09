from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class ConsultationPagination(PageNumberPagination):
    """
    Custom pagination class for consultation requests to provide a consistent
    response structure across the API.
    """
    page_size = 10  # Default number of items per page
    page_size_query_param = 'page_size'  # Allows client to set page size e.g., ?page_size=20
    max_page_size = 100  # Maximum page size the client can request

    def get_paginated_response(self, data):
        """
        Overrides the default paginated response to match the project's standard format.
        """
        return Response({
            'message': 'Consultations retrieved successfully',
            'data': {
                'consultations': data,
                'pagination': {
                    'current_page': self.page.number,
                    'total_pages': self.page.paginator.num_pages,
                    'total_items': self.page.paginator.count,
                    'has_next': self.page.has_next(),
                    'has_previous': self.page.has_previous(),
                    'page_size': self.get_page_size(self.request)
                }
            }
        })