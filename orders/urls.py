from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_order, name='create_order'),
    path('my-orders/', views.user_orders, name='user_orders'),
    path('<uuid:order_id>/', views.order_detail, name='order_detail'),
    path('track/<str:order_number>/', views.order_by_number, name='order_by_number'),
    path('<uuid:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('summary/', views.order_summary, name='order_summary'),
    path('stats/', views.order_stats, name='order_stats'),

    # Loyalty endpoints
    path('loyalty/account/', views.loyalty_account, name='loyalty_account'),
    
    # Shipping addresses endpoints
    path('shipping-addresses/', views.shipping_addresses, name='shipping_addresses'),
    path('shipping-addresses/<uuid:address_id>/', views.shipping_address_detail, name='shipping_address_detail'),
    path('shipping-addresses/<uuid:address_id>/set-default/', views.set_default_address, name='set_default_address'),
]
