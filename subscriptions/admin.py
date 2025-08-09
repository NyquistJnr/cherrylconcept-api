from django.contrib import admin
from .models import Subscription

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at')
    search_fields = ('email',)
    list_filter = ('created_at',)
    readonly_fields = ('id', 'created_at')
    ordering = ('-created_at',)
