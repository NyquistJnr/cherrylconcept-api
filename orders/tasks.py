from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_webhook_event_async(self, event_data):
    """Process Paystack webhook event asynchronously"""
    try:
        from .paystack_utils import PaystackWebhookProcessor
        
        processor = PaystackWebhookProcessor()
        success = processor.process_webhook_event(event_data)
        
        if not success:
            # Retry with exponential backoff
            countdown = 2 ** self.request.retries * 60  # 1min, 2min, 4min
            raise self.retry(countdown=countdown)
        
        return f"Successfully processed webhook event: {event_data.get('event')}"
        
    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}")
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries * 60
            raise self.retry(countdown=countdown, exc=e)
        else:
            # Final failure - send alert to admin
            send_webhook_failure_alert.delay(event_data, str(e))
            raise

@shared_task
def send_payment_confirmation_email(order_id):
    """Send payment confirmation email to customer"""
    try:
        from .models import Order
        
        order = Order.objects.get(id=order_id)
        
        subject = f'Payment Confirmation - Order {order.order_number}'
        
        html_message = render_to_string('emails/payment_confirmation.html', {
            'order': order,
            'customer_name': order.customer_full_name,
            'items': order.items.all(),
        })
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer_email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Payment confirmation email sent for order {order.order_number}")
        return f"Payment confirmation email sent to {order.customer_email}"
        
    except Exception as e:
        logger.error(f"Failed to send payment confirmation email: {str(e)}")
        raise

@shared_task
def send_payment_failed_email(order_id):
    """Send payment failed notification email"""
    try:
        from .models import Order
        
        order = Order.objects.get(id=order_id)
        
        subject = f'Payment Failed - Order {order.order_number}'
        
        html_message = render_to_string('emails/payment_failed.html', {
            'order': order,
            'customer_name': order.customer_full_name,
            'retry_url': f"{settings.FRONTEND_URL}/payment/retry/{order.id}",
        })
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer_email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Payment failed email sent for order {order.order_number}")
        return f"Payment failed email sent to {order.customer_email}"
        
    except Exception as e:
        logger.error(f"Failed to send payment failed email: {str(e)}")
        raise

@shared_task
def send_webhook_failure_alert(event_data, error_message):
    """Send alert to admin when webhook processing fails completely"""
    try:
        subject = 'Paystack Webhook Processing Failed'
        
        message = f"""
        Webhook processing failed after all retries.
        
        Event Type: {event_data.get('event')}
        Event ID: {event_data.get('data', {}).get('id')}
        Reference: {event_data.get('data', {}).get('reference')}
        Error: {error_message}
        
        Please investigate and handle manually if needed.
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=False,
        )
        
        logger.info("Webhook failure alert sent to admin")
        
    except Exception as e:
        logger.error(f"Failed to send webhook failure alert: {str(e)}")

@shared_task
def cleanup_old_webhook_events():
    """Clean up old webhook events (run daily)"""
    try:
        from .models import PaystackEvent
        from django.utils import timezone
        from datetime import timedelta
        
        # Delete processed events older than 30 days
        cutoff_date = timezone.now() - timedelta(days=30)
        deleted_count = PaystackEvent.objects.filter(
            processed=True,
            created_at__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old webhook events")
        return f"Cleaned up {deleted_count} old webhook events"
        
    except Exception as e:
        logger.error(f"Failed to cleanup old webhook events: {str(e)}")
        raise

@shared_task
def retry_failed_webhook_events():
    """Retry failed webhook events (run hourly)"""
    try:
        from .models import PaystackEvent
        from .paystack_utils import PaystackWebhookProcessor
        
        # Get unprocessed events with less than 5 attempts
        failed_events = PaystackEvent.objects.filter(
            processed=False,
            processing_attempts__lt=5
        )[:10]  # Limit to 10 events per run
        
        processor = PaystackWebhookProcessor()
        success_count = 0
        
        for event in failed_events:
            try:
                success = processor.process_webhook_event(event.event_data)
                if success:
                    success_count += 1
                    logger.info(f"Successfully retried webhook event {event.event_id}")
            except Exception as e:
                logger.error(f"Retry failed for webhook event {event.event_id}: {str(e)}")
        
        return f"Retried {len(failed_events)} events, {success_count} succeeded"
        
    except Exception as e:
        logger.error(f"Failed to retry webhook events: {str(e)}")
        raise
