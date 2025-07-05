import hashlib
import hmac
import json
import requests
import logging
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class PaystackAPI:
    """Secure Paystack API client with proper error handling"""
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.public_key = settings.PAYSTACK_PUBLIC_KEY
        self.base_url = "https://api.paystack.co"
        self.webhook_secret = settings.PAYSTACK_WEBHOOK_SECRET
        
        if not all([self.secret_key, self.public_key]):
            raise ValueError("Paystack keys not properly configured")
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """Make secure API request to Paystack"""
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
            "User-Agent": "Django-Ecommerce/1.0"
        }
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack API request failed: {str(e)}")
            raise Exception(f"Payment service unavailable: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Paystack: {str(e)}")
            raise Exception("Invalid response from payment service")
    
    def initialize_transaction(self, order) -> Dict[str, Any]:
        """Initialize payment transaction with Paystack"""
        payload = {
            "reference": order.payment_reference,
            "amount": order.get_amount_in_kobo(),  # Paystack expects amount in kobo
            "email": order.customer_email,
            "currency": order.currency,
            # "callback_url": f"{settings.FRONTEND_URL}/payment/callback",
            "metadata": {
                "order_id": str(order.id),
                "order_number": order.order_number,
                "customer_name": order.customer_full_name,
                "customer_phone": order.customer_phone,
                "items_count": order.items.count(),
            },
            "channels": ["card", "bank", "ussd", "qr", "bank_transfer"],
            "split_code": None,  # For marketplace transactions
        }
        
        try:
            response = self._make_request('POST', '/transaction/initialize', payload)
            
            if response.get('status'):
                data = response.get('data', {})
                
                # Update order with Paystack details
                order.paystack_reference = data.get('reference', '')
                order.paystack_access_code = data.get('access_code', '')
                order.save(update_fields=['paystack_reference', 'paystack_access_code'])
                
                return {
                    'status': True,
                    'authorization_url': data.get('authorization_url'),
                    'access_code': data.get('access_code'),
                    'reference': data.get('reference'),
                }
            else:
                raise Exception(response.get('message', 'Transaction initialization failed'))
                
        except Exception as e:
            logger.error(f"Failed to initialize Paystack transaction for order {order.order_number}: {str(e)}")
            raise
    
    def verify_transaction(self, reference: str) -> Dict[str, Any]:
        """Verify transaction with Paystack"""
        try:
            response = self._make_request('GET', f'/transaction/verify/{reference}')
            
            if response.get('status'):
                return response.get('data', {})
            else:
                raise Exception(response.get('message', 'Transaction verification failed'))
                
        except Exception as e:
            logger.error(f"Failed to verify Paystack transaction {reference}: {str(e)}")
            raise
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Paystack webhook signature for security"""
        try:
            # Paystack sends signature as 'sha512=<hash>'
            if not signature.startswith('sha512='):
                logger.warning("Invalid webhook signature format")
                return False
            
            # Extract the hash part
            received_hash = signature[7:]  # Remove 'sha512=' prefix
            
            # Compute expected signature
            expected_signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha512
            ).hexdigest()
            
            # Secure comparison to prevent timing attacks
            return hmac.compare_digest(expected_signature, received_hash)
            
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            return False
    
    def refund_transaction(self, transaction_reference: str, amount: Optional[int] = None) -> Dict[str, Any]:
        """Refund a transaction"""
        payload = {
            "transaction": transaction_reference,
        }
        
        if amount:
            payload["amount"] = amount  # Amount in kobo
        
        try:
            response = self._make_request('POST', '/refund', payload)
            
            if response.get('status'):
                return response.get('data', {})
            else:
                raise Exception(response.get('message', 'Refund failed'))
                
        except Exception as e:
            logger.error(f"Failed to refund Paystack transaction {transaction_reference}: {str(e)}")
            raise
    
    def get_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """Get transaction details by ID"""
        try:
            response = self._make_request('GET', f'/transaction/{transaction_id}')
            
            if response.get('status'):
                return response.get('data', {})
            else:
                raise Exception(response.get('message', 'Failed to get transaction'))
                
        except Exception as e:
            logger.error(f"Failed to get Paystack transaction {transaction_id}: {str(e)}")
            raise

class PaystackWebhookProcessor:
    """Process Paystack webhook events securely"""
    
    def __init__(self):
        self.paystack_api = PaystackAPI()
    
    def process_webhook_event(self, event_data: Dict[str, Any]) -> bool:
        """Process webhook event and update order status"""
        from .models import Order, PaystackEvent, PaymentTransaction
        
        event_type = event_data.get('event')
        data = event_data.get('data', {})
        
        try:
            # Store the webhook event for audit
            paystack_event, created = PaystackEvent.objects.get_or_create(
                event_id=data.get('id', ''),
                defaults={
                    'event_type': event_type,
                    'event_data': event_data,
                }
            )
            
            if not created and paystack_event.processed:
                logger.info(f"Webhook event {paystack_event.event_id} already processed")
                return True
            
            paystack_event.increment_processing_attempts()
            
            # Process different event types
            if event_type == 'charge.success':
                success = self._process_successful_payment(data, paystack_event)
            elif event_type in ['charge.failed', 'charge.abandoned']:
                success = self._process_failed_payment(data, paystack_event)
            else:
                logger.info(f"Unhandled webhook event type: {event_type}")
                success = True  # Don't retry unknown events
            
            if success:
                paystack_event.mark_as_processed()
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing webhook event {event_type}: {str(e)}")
            if 'paystack_event' in locals():
                paystack_event.increment_processing_attempts(str(e))
            return False
    
    def _process_successful_payment(self, data: Dict[str, Any], paystack_event) -> bool:
        """Process successful payment webhook"""
        from .models import Order, PaymentTransaction
        
        try:
            reference = data.get('reference')
            if not reference:
                raise ValueError("No reference in webhook data")
            
            # Find the order
            order = Order.objects.get(payment_reference=reference)
            paystack_event.order = order
            paystack_event.save()
            
            # Verify transaction with Paystack API for security
            verification_data = self.paystack_api.verify_transaction(reference)
            
            if verification_data.get('status') != 'success':
                raise ValueError(f"Transaction verification failed: {verification_data.get('gateway_response')}")
            
            # Create/update payment transaction record
            transaction, created = PaymentTransaction.objects.get_or_create(
                reference=reference,
                defaults={
                    'order': order,
                    'paystack_reference': data.get('id', ''),
                    'amount': Decimal(str(data.get('amount', 0))) / 100,  # Convert from kobo
                    'currency': data.get('currency', 'NGN'),
                    'status': 'success',
                    'gateway_response': data.get('gateway_response', ''),
                    'paid_at': timezone.now(),
                    'channel': data.get('channel', ''),
                    'fees': Decimal(str(data.get('fees', 0))) / 100,
                    'authorization_code': data.get('authorization', {}).get('authorization_code', ''),
                    'card_type': data.get('authorization', {}).get('card_type', ''),
                    'bank': data.get('authorization', {}).get('bank', ''),
                    'last_4': data.get('authorization', {}).get('last4', ''),
                    'metadata': data.get('metadata', {}),
                }
            )
            
            if not created:
                # Update existing transaction
                transaction.status = 'success'
                transaction.paid_at = timezone.now()
                transaction.gateway_response = data.get('gateway_response', '')
                transaction.save()
            
            # Update order status
            order.payment_status = 'success'
            order.status = 'paid'
            order.payment_method = data.get('channel', '')
            order.paid_amount = transaction.amount
            order.payment_date = transaction.paid_at
            order.save()
            
            # Award loyalty points if applicable
            order.award_loyalty_points()
            
            logger.info(f"Successfully processed payment for order {order.order_number}")
            return True
            
        except Order.DoesNotExist:
            logger.error(f"Order not found for payment reference: {reference}")
            return True  # Don't retry if order doesn't exist
        except Exception as e:
            logger.error(f"Error processing successful payment: {str(e)}")
            return False
    
    def _process_failed_payment(self, data: Dict[str, Any], paystack_event) -> bool:
        """Process failed payment webhook"""
        from .models import Order, PaymentTransaction
        
        try:
            reference = data.get('reference')
            if not reference:
                raise ValueError("No reference in webhook data")
            
            # Find the order
            order = Order.objects.get(payment_reference=reference)
            paystack_event.order = order
            paystack_event.save()
            
            # Create/update payment transaction record
            transaction, created = PaymentTransaction.objects.get_or_create(
                reference=reference,
                defaults={
                    'order': order,
                    'paystack_reference': data.get('id', ''),
                    'amount': Decimal(str(data.get('amount', 0))) / 100,
                    'currency': data.get('currency', 'NGN'),
                    'status': 'failed',
                    'gateway_response': data.get('gateway_response', ''),
                    'channel': data.get('channel', ''),
                    'metadata': data.get('metadata', {}),
                }
            )
            
            if not created:
                transaction.status = 'failed'
                transaction.gateway_response = data.get('gateway_response', '')
                transaction.save()
            
            # Update order status
            order.payment_status = 'failed'
            order.status = 'failed'
            order.save()
            
            logger.info(f"Processed failed payment for order {order.order_number}")
            return True
            
        except Order.DoesNotExist:
            logger.error(f"Order not found for payment reference: {reference}")
            return True  # Don't retry if order doesn't exist
        except Exception as e:
            logger.error(f"Error processing failed payment: {str(e)}")
            return False
