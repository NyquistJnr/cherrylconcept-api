from django.contrib import admin
from .models import Consultation

@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = (
        'full_name', 
        'email', 
        'consultation_time', 
        'user', 
        'created_at'
    )
    list_filter = ('consultation_time', 'created_at')
    search_fields = ('full_name', 'email', 'user__email')
    readonly_fields = ('id', 'created_at')
    
    fieldsets = (
        (None, {
            'fields': ('id', 'full_name', 'email', 'message')
        }),
        ('Scheduling', {
            'fields': ('consultation_time', 'user')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
