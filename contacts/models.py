import uuid
from django.db import models

class ContactMessage(models.Model):
    """
    Model to store messages submitted through the contact form.
    """
    class DepartmentChoices(models.TextChoices):
        GENERAL = 'general', 'General Inquiry'
        SALES = 'sales', 'Sales & Orders'
        SUPPORT = 'support', 'Customer Support'
        PARTNERSHIPS = 'partnerships', 'Partnerships & Press'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20, blank=True, help_text="Optional phone number.")
    department = models.CharField(
        max_length=20,
        choices=DepartmentChoices.choices,
        default=DepartmentChoices.GENERAL
    )
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'contact_messages'
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'
        ordering = ['-created_at']

    def __str__(self):
        return f"Message from {self.first_name} {self.last_name} - {self.subject}"
