from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal
import random
import string
import uuid

User = get_user_model()

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('paid', 'Payment Confirmed'),
        ('confirmed', 'Order Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('failed', 'Payment Failed'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=20, unique=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='orders')
    
    # Customer Information (required for both logged in and guest users)
    customer_email = models.EmailField()
    customer_first_name = models.CharField(max_length=100)
    customer_last_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=20)
    
    # Shipping Information
    shipping_address_line1 = models.CharField(max_length=255)
    shipping_address_line2 = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100)
    
    # Order Details
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default='NGN')
    
    # Payment Information
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_reference = models.CharField(max_length=255, unique=True, blank=True)
    paystack_reference = models.CharField(max_length=255, blank=True)
    paystack_access_code = models.CharField(max_length=255, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    
    # Order Status & Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    
    # Loyalty Points
    loyalty_points_earned = models.PositiveIntegerField(default=0)
    loyalty_points_used = models.PositiveIntegerField(default=0)
    loyalty_points_awarded = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'orders'
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment_reference']),
            models.Index(fields=['paystack_reference']),
            models.Index(fields=['customer_email']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_status']),
        ]
    
    def __str__(self):
        return f"Order {self.order_number} - {self.customer_first_name} {self.customer_last_name}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        if not self.payment_reference:
            self.payment_reference = self.generate_payment_reference()
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        """Generate unique order number"""
        import random
        import string
        while True:
            order_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not Order.objects.filter(order_number=order_number).exists():
                return order_number
    
    def generate_payment_reference(self):
        """Generate unique payment reference for Paystack"""
        import time
        timestamp = str(int(time.time()))
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"order_{self.id}_{timestamp}_{random_suffix}"
    
    @property
    def customer_full_name(self):
        return f"{self.customer_first_name} {self.customer_last_name}"
    
    @property
    def shipping_address(self):
        """Return formatted shipping address"""
        address = f"{self.shipping_address_line1}"
        if self.shipping_address_line2:
            address += f", {self.shipping_address_line2}"
        address += f", {self.shipping_city}, {self.shipping_state} {self.shipping_postal_code}, {self.shipping_country}"
        return address
    
    def calculate_loyalty_points(self):
        """Calculate loyalty points earned (5% of subtotal)"""
        if self.user:  # Only logged in users earn points
            return int(self.subtotal * Decimal('0.05'))
        return 0
    
    def award_loyalty_points(self):
        """Award loyalty points after successful payment"""
        if self.user and not self.loyalty_points_awarded and self.payment_status == 'success':
            loyalty_account, created = LoyaltyAccount.objects.get_or_create(user=self.user)
            points_to_award = self.calculate_loyalty_points()
            
            if points_to_award > 0:
                loyalty_account.add_points(points_to_award, self)
                self.loyalty_points_earned = points_to_award
                self.loyalty_points_awarded = True
                self.save(update_fields=['loyalty_points_earned', 'loyalty_points_awarded'])
    
    def get_amount_in_kobo(self):
        """Convert amount to kobo for Paystack (multiply by 100)"""
        return int(self.total_amount * 100)

class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    
    # Product details at time of purchase (for record keeping)
    product_name = models.CharField(max_length=200)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Order item specifics
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    color = models.CharField(max_length=50, blank=True)
    size = models.CharField(max_length=20, blank=True)
    
    # Calculated fields
    line_total = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'order_items'
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
    
    def save(self, *args, **kwargs):
        self.line_total = self.product_price * self.quantity
        super().save(*args, **kwargs)

class LoyaltyAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='loyalty_account')
    total_points_earned = models.PositiveIntegerField(default=0)
    total_points_used = models.PositiveIntegerField(default=0)
    current_balance = models.PositiveIntegerField(default=0)
    tier = models.CharField(max_length=20, default='Bronze')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'loyalty_accounts'
        verbose_name = 'Loyalty Account'
        verbose_name_plural = 'Loyalty Accounts'
    
    def __str__(self):
        return f"{self.user.full_name} - {self.current_balance} points"
    
    def add_points(self, points, order=None):
        """Add points to account"""
        self.total_points_earned += points
        self.current_balance += points
        self.update_tier()
        self.save()
        
        # Create transaction record
        LoyaltyTransaction.objects.create(
            account=self,
            transaction_type='earned',
            points=points,
            order=order,
            description=f"Points earned from order {order.order_number if order else 'N/A'}"
        )
    
    def use_points(self, points, order=None):
        """Use points from account"""
        if self.current_balance >= points:
            self.total_points_used += points
            self.current_balance -= points
            self.save()
            
            # Create transaction record
            LoyaltyTransaction.objects.create(
                account=self,
                transaction_type='used',
                points=points,
                order=order,
                description=f"Points used for order {order.order_number if order else 'N/A'}"
            )
            return True
        return False
    
    def update_tier(self):
        """Update user tier based on total points earned"""
        if self.total_points_earned >= 10000:
            self.tier = 'Platinum'
        elif self.total_points_earned >= 5000:
            self.tier = 'Gold'
        elif self.total_points_earned >= 1000:
            self.tier = 'Silver'
        else:
            self.tier = 'Bronze'

class LoyaltyTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('earned', 'Points Earned'),
        ('used', 'Points Used'),
        ('expired', 'Points Expired'),
        ('bonus', 'Bonus Points'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(LoyaltyAccount, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    points = models.IntegerField()
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'loyalty_transactions'
        verbose_name = 'Loyalty Transaction'
        verbose_name_plural = 'Loyalty Transactions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.account.user.full_name} - {self.transaction_type} {self.points} points"

class ShippingAddress(models.Model):
    """Saved shipping addresses for logged in users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shipping_addresses')
    label = models.CharField(max_length=50, help_text="e.g., Home, Office, etc.")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shipping_addresses'
        verbose_name = 'Shipping Address'
        verbose_name_plural = 'Shipping Addresses'
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.user.full_name} - {self.label}"
    
    def save(self, *args, **kwargs):
        # If this is set as default, unset other default addresses
        if self.is_default:
            ShippingAddress.objects.filter(user=self.user, is_default=True).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def formatted_address(self):
        """Return formatted address"""
        address = f"{self.address_line1}"
        if self.address_line2:
            address += f", {self.address_line2}"
        address += f", {self.city}, {self.state} {self.postal_code}, {self.country}"
        return address

class PaystackEvent(models.Model):
    """Store Paystack webhook events for audit and replay"""
    EVENT_TYPES = [
        ('charge.success', 'Charge Success'),
        ('charge.failed', 'Charge Failed'),
        ('invoice.create', 'Invoice Create'),
        ('invoice.update', 'Invoice Update'),
        ('subscription.create', 'Subscription Create'),
        ('subscription.disable', 'Subscription Disable'),
        ('transfer.success', 'Transfer Success'),
        ('transfer.failed', 'Transfer Failed'),
        ('transfer.reversed', 'Transfer Reversed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.CharField(max_length=255, unique=True, help_text="Paystack event ID")
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    event_data = models.JSONField(help_text="Complete webhook payload")
    processed = models.BooleanField(default=False)
    processing_attempts = models.PositiveIntegerField(default=0)
    last_processing_error = models.TextField(blank=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='paystack_events')
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'paystack_events'
        verbose_name = 'Paystack Event'
        verbose_name_plural = 'Paystack Events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_id']),
            models.Index(fields=['event_type']),
            models.Index(fields=['processed']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Paystack Event {self.event_type} - {self.event_id}"
    
    def mark_as_processed(self):
        """Mark event as successfully processed"""
        from django.utils import timezone
        self.processed = True
        self.processed_at = timezone.now()
        self.save(update_fields=['processed', 'processed_at'])
    
    def increment_processing_attempts(self, error_message=None):
        """Increment processing attempts and optionally store error"""
        self.processing_attempts += 1
        if error_message:
            self.last_processing_error = str(error_message)
        self.save(update_fields=['processing_attempts', 'last_processing_error'])

class PaymentTransaction(models.Model):
    """Detailed payment transaction records"""
    TRANSACTION_STATUS = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('abandoned', 'Abandoned'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payment_transactions')
    reference = models.CharField(max_length=255, unique=True)
    paystack_reference = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='NGN')
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS, default='pending')
    gateway_response = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    channel = models.CharField(max_length=50, blank=True, help_text="Payment channel (card, bank, ussd, etc.)")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    fees = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    authorization_code = models.CharField(max_length=255, blank=True)
    card_type = models.CharField(max_length=50, blank=True)
    bank = models.CharField(max_length=100, blank=True)
    last_4 = models.CharField(max_length=4, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payment_transactions'
        verbose_name = 'Payment Transaction'
        verbose_name_plural = 'Payment Transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['paystack_reference']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Payment {self.reference} - {self.status} - ₦{self.amount}"
