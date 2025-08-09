from django.contrib import admin
from .models import ContactMessage

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'first_name', 'last_name', 'email', 'department', 'created_at')
    list_filter = ('department', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'subject', 'message')
    readonly_fields = ('id', 'created_at', 'first_name', 'last_name', 'email', 'phone_number', 'department', 'subject', 'message')
    ordering = ('-created_at',)

    fieldsets = (
        ('Contact Information', {
            'fields': ('first_name', 'last_name', 'email', 'phone_number')
        }),
        ('Message Details', {
            'fields': ('department', 'subject', 'message')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at')
        }),
    )

    # Make all fields read-only in the admin change view
    def has_change_permission(self, request, obj=None):
        return False
