# products/pagination.py

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class ProductPagination(PageNumberPagination):
    """
    Custom pagination class for products to provide a consistent
    and detailed response structure.
    """
    page_size = 6  # The default number of products to show per page
    page_size_query_param = 'page_size'  # Allows client to request a page size, e.g., ?page_size=24
    max_page_size = 100  # The largest page size a client can request

    def get_paginated_response(self, data):
        """
        Overrides the default response format to match your desired structure.
        """
        # Set a default message
        message = 'Products retrieved successfully'
        
        # Allow views to override the message by setting a 'custom_message' attribute on the request
        if hasattr(self.request, 'custom_message'):
            message = self.request.custom_message

        return Response({
            'message': message,
            'data': {
                'products': data, # The paginated list of products
                'pagination': {
                    'current_page': self.page.number,
                    'total_pages': self.page.paginator.num_pages,
                    'total_items': self.page.paginator.count,
                    'page_size': self.get_page_size(self.request),
                    'has_next': self.page.has_next(),
                    'has_previous': self.page.has_previous()
                }
            }
        })
