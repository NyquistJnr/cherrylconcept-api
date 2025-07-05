from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from .models import Order, OrderItem, LoyaltyAccount, LoyaltyTransaction, ShippingAddress

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['line_total']
    fields = ['product', 'product_name', 'product_price', 'quantity', 'color', 'size', 'line_total']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'customer_full_name', 'customer_email', 'total_amount', 
        'status', 'loyalty_points_earned', 'created_at', 'user_link'
    ]
    list_filter = ['status', 'created_at', 'shipping_country']
    search_fields = [
        'order_number', 'customer_email', 'customer_first_name', 
        'customer_last_name', 'customer_phone'
    ]
    readonly_fields = [
        'order_number', 'created_at', 'updated_at', 'loyalty_points_earned'
    ]
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status', 'notes', 'tracking_number')
        }),
        ('Customer Information', {
            'fields': (
                'customer_email', 'customer_first_name', 'customer_last_name', 
                'customer_phone'
            )
        }),
        ('Shipping Address', {
            'fields': (
                'shipping_address_line1', 'shipping_address_line2', 'shipping_city',
                'shipping_state', 'shipping_postal_code', 'shipping_country'
            )
        }),
        ('Order Totals', {
            'fields': (
                'subtotal', 'shipping_fee', 'tax_amount', 'total_amount',
                'loyalty_points_earned', 'loyalty_points_used'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at', 'confirmed_at', 
                'shipped_at', 'delivered_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:accounts_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.full_name)
        return "Guest"
    user_link.short_description = 'User'
    
    def save_model(self, request, obj, form, change):
        if change and 'status' in form.changed_data:
            # Update timestamps based on status change
            from django.utils import timezone
            if obj.status == 'confirmed' and not obj.confirmed_at:
                obj.confirmed_at = timezone.now()
            elif obj.status == 'shipped' and not obj.shipped_at:
                obj.shipped_at = timezone.now()
            elif obj.status == 'delivered' and not obj.delivered_at:
                obj.delivered_at = timezone.now()
        super().save_model(request, obj, form, change)

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product_name', 'quantity', 'product_price', 'line_total']
    list_filter = ['order__status', 'order__created_at']
    search_fields = ['order__order_number', 'product_name', 'product__name']
    readonly_fields = ['line_total']

class LoyaltyTransactionInline(admin.TabularInline):
    model = LoyaltyTransaction
    extra = 0
    readonly_fields = ['created_at']
    fields = ['transaction_type', 'points', 'order', 'description', 'created_at']

@admin.register(LoyaltyAccount)
class LoyaltyAccountAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'current_balance', 'total_points_earned', 'total_points_used', 
        'tier', 'created_at'
    ]
    list_filter = ['tier', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['total_points_earned', 'total_points_used', 'created_at', 'updated_at']
    inlines = [LoyaltyTransactionInline]
    
    fieldsets = (
        ('Account Information', {
            'fields': ('user', 'tier')
        }),
        ('Points Summary', {
            'fields': ('current_balance', 'total_points_earned', 'total_points_used')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = ['account', 'transaction_type', 'points', 'order', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['account__user__email', 'description', 'order__order_number']
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('account__user', 'order')

@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'label', 'full_name', 'city', 'country', 'is_default', 'created_at']
    list_filter = ['is_default', 'country', 'created_at']
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'first_name', 'last_name', 'city', 'label'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User & Label', {
            'fields': ('user', 'label', 'is_default')
        }),
        ('Contact Information', {
            'fields': ('first_name', 'last_name', 'phone_number')
        }),
        ('Address Information', {
            'fields': (
                'address_line1', 'address_line2', 'city', 
                'state', 'postal_code', 'country'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
