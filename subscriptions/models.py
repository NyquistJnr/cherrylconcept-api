import uuid
from django.db import models

class Subscription(models.Model):
    """
    Model to store email addresses for a subscription list.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, help_text="The email address of the subscriber.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'subscriptions'
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'
        ordering = ['-created_at']

    def __str__(self):
        return self.email
