from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags

@shared_task
def send_password_reset_email(user_email, reset_url, user_name):
    """Send password reset email asynchronously"""
    subject = 'Password Reset Request'
    
    html_message = render_to_string('emails/password_reset.html', {
        'user_name': user_name,
        'reset_url': reset_url,
    })
    
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )
        return f"Password reset email sent to {user_email}"
    except Exception as e:
        return f"Failed to send email: {str(e)}"
