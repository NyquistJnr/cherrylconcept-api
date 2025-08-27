from django.urls import path
from . import views
from .paystack_views import (
    initialize_payment, 
    verify_payment, 
    PaystackWebhookView, 
    refund_payment, 
    payment_status
)

urlpatterns = [
    path('create/', views.create_order, name='create_order'),
    path('my-orders/', views.user_orders, name='user_orders'),
    path('<uuid:order_id>/', views.order_detail, name='order_detail'),
    path('track/<str:order_number>/', views.order_by_number, name='order_by_number'),
    path('<uuid:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('summary/', views.order_summary, name='order_summary'),
    path('stats/', views.order_stats, name='order_stats'),

    path('admin/all/', views.admin_all_orders, name='admin_all_orders'),
    path('admin/users/<uuid:user_id>/loyalty/', views.admin_user_loyalty_account, name='admin_user_loyalty_account'),
    path('admin/users/<uuid:user_id>/orders/', views.admin_user_order_history, name='admin_user_order_history'),


    # Loyalty endpoints
    path('loyalty/account/', views.loyalty_account, name='loyalty_account'),

     # Payment endpoints
    path('payments/initialize/<uuid:order_id>/', initialize_payment, name='initialize_payment'),
    path('payments/verify/<str:reference>/', verify_payment, name='verify_payment'),
    path('payments/webhook/', PaystackWebhookView.as_view(), name='paystack_webhook'),
    path('payments/refund/<uuid:order_id>/', refund_payment, name='refund_payment'),
    path('payments/status/<uuid:order_id>/', payment_status, name='payment_status'),
    
    # Shipping addresses endpoints
    path('shipping-addresses/', views.shipping_addresses, name='shipping_addresses'),
    path('shipping-addresses/<uuid:address_id>/', views.shipping_address_detail, name='shipping_address_detail'),
    path('shipping-addresses/<uuid:address_id>/set-default/', views.set_default_address, name='set_default_address'),
]
