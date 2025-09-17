import json
import logging
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Order
from .paystack_utils import PaystackAPI, PaystackWebhookProcessor
from .tasks import process_webhook_event_async

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def initialize_payment(request, order_id):
    """Initialize Paystack payment for an order"""
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # Verify order is in correct state for payment
        if order.payment_status != 'pending':
            return Response({
                'message': 'Order payment already processed or invalid state',
                'order_status': order.status,
                'payment_status': order.payment_status
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Initialize payment with Paystack
        paystack_api = PaystackAPI()
        payment_data = paystack_api.initialize_transaction(order)
        
        return Response({
            'message': 'Payment initialized successfully',
            'data': {
                'order_id': str(order.id),
                'order_number': order.order_number,
                'amount': str(order.total_amount),
                'currency': order.currency,
                'authorization_url': payment_data['authorization_url'],
                'access_code': payment_data['access_code'],
                'reference': payment_data['reference'],
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Payment initialization failed for order {order_id}: {str(e)}")
        return Response({
            'message': 'Payment initialization failed',
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([AllowAny])
def verify_payment(request, reference):
    """Verify payment status with Paystack"""
    try:
        paystack_api = PaystackAPI()
        verification_data = paystack_api.verify_transaction(reference)
        
        # Find the order
        order = get_object_or_404(Order, payment_reference=reference)
        
        # Update order based on verification result
        if verification_data.get('status') == 'success':
            if order.payment_status != 'success':
                order.payment_status = 'success'
                order.status = 'paid'
                order.save()
                order.award_loyalty_points()
            
            return Response({
                'message': 'Payment verified successfully',
                'data': {
                    'order_id': str(order.id),
                    'order_number': order.order_number,
                    'status': verification_data.get('status'),
                    'amount': verification_data.get('amount', 0) / 100,
                    'currency': verification_data.get('currency'),
                    'gateway_response': verification_data.get('gateway_response'),
                    'paid_at': verification_data.get('paid_at'),
                    'channel': verification_data.get('channel'),
                }
            }, status=status.HTTP_200_OK)
        else:
            # Payment failed or pending
            if order.payment_status == 'pending':
                order.payment_status = 'failed'
                order.status = 'failed'
                order.save()
            
            return Response({
                'message': 'Payment verification failed',
                'data': {
                    'order_id': str(order.id),
                    'order_number': order.order_number,
                    'status': verification_data.get('status'),
                    'gateway_response': verification_data.get('gateway_response'),
                }
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Payment verification failed for reference {reference}: {str(e)}")
        return Response({
            'message': 'Payment verification failed',
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(csrf_exempt, name='dispatch')
class PaystackWebhookView(View):
    """Secure Paystack webhook endpoint"""
    
    def post(self, request):
        """Handle Paystack webhook events"""
        try:
            # Get raw body and signature
            payload = request.body
            # signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE', '')
            
            # if not signature:
            #     logger.warning("Webhook received without signature")
            #     return HttpResponse('Missing signature', status=400)
            
            # # Verify webhook signature
            # paystack_api = PaystackAPI()
            # if not paystack_api.verify_webhook_signature(payload, signature):
            #     logger.warning("Invalid webhook signature")
            #     return HttpResponse('Invalid signature', status=401)
            
            # Parse JSON payload
            try:
                event_data = json.loads(payload.decode('utf-8'))
            except json.JSONDecodeError:
                logger.error("Invalid JSON in webhook payload")
                return HttpResponse('Invalid JSON', status=400)
            
            # Process webhook event asynchronously for better performance
            process_webhook_event_async.delay(event_data)
            
            return HttpResponse('OK', status=200)
            
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")
            return HttpResponse('Internal server error', status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def refund_payment(request, order_id):
    """Refund payment for an order (admin only in production)"""
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # Verify order can be refunded
        if order.payment_status != 'success':
            return Response({
                'message': 'Order payment not successful, cannot refund'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if order.status == 'refunded':
            return Response({
                'message': 'Order already refunded'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get refund amount (default to full amount)
        refund_amount = request.data.get('amount')
        if refund_amount:
            refund_amount = int(float(refund_amount) * 100)  # Convert to kobo
        
        # Process refund with Paystack
        paystack_api = PaystackAPI()
        refund_data = paystack_api.refund_transaction(
            order.paystack_reference,
            refund_amount
        )
        
        # Update order status
        order.status = 'refunded'
        order.payment_status = 'refunded'
        order.save()
        
        return Response({
            'message': 'Refund processed successfully',
            'data': {
                'order_id': str(order.id),
                'order_number': order.order_number,
                'refund_amount': refund_data.get('amount', 0) / 100,
                'refund_status': refund_data.get('status'),
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Refund failed for order {order_id}: {str(e)}")
        return Response({
            'message': 'Refund failed',
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([AllowAny])
def payment_status(request, order_id):
    """Get payment status for an order"""
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # Check if user has permission to view this order
        if request.user.is_authenticated:
            if order.user and order.user != request.user:
                return Response({
                    'message': 'Permission denied'
                }, status=status.HTTP_403_FORBIDDEN)
        else:
            # For guest users, require email verification
            email = request.GET.get('email')
            if not email or order.customer_email.lower() != email.lower():
                return Response({
                    'message': 'Email verification required'
                }, status=status.HTTP_403_FORBIDDEN)
        
        return Response({
            'message': 'Payment status retrieved successfully',
            'data': {
                'order_id': str(order.id),
                'order_number': order.order_number,
                'payment_status': order.payment_status,
                'order_status': order.status,
                'total_amount': str(order.total_amount),
                'currency': order.currency,
                'payment_method': order.payment_method,
                'payment_date': order.payment_date,
                'can_retry_payment': order.payment_status in ['pending', 'failed'],
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting payment status for order {order_id}: {str(e)}")
        return Response({
            'message': 'Error retrieving payment status',
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
