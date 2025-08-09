import uuid
from django.db import models
from django.conf import settings

class Consultation(models.Model):
    """
    Model to store consultation requests from both registered users and anonymous visitors.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # ForeignKey to the User model. It's optional (nullable) to allow anonymous submissions.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='consultations'
    )
    
    # Fields for all users (logged-in or anonymous)
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    
    # Optional message from the user
    message = models.TextField(blank=True, null=True)
    
    # The requested date and time for the consultation
    consultation_time = models.DateTimeField()
    
    # Timestamp for when the request was created
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'consultations'
        verbose_name = 'Consultation'
        verbose_name_plural = 'Consultations'
        ordering = ['-created_at']

    def __str__(self):
        return f"Consultation request from {self.full_name} for {self.consultation_time.strftime('%Y-%m-%d %H:%M')}"
