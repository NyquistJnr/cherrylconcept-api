from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid

User = get_user_model()

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
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
    
    # Order Status & Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    
    # Loyalty Points
    loyalty_points_earned = models.PositiveIntegerField(default=0)
    loyalty_points_used = models.PositiveIntegerField(default=0)
    
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
    
    def __str__(self):
        return f"Order {self.order_number} - {self.customer_first_name} {self.customer_last_name}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        """Generate unique order number"""
        import random
        import string
        while True:
            order_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not Order.objects.filter(order_number=order_number).exists():
                return order_number
    
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
        """Calculate loyalty points earned (2% of subtotal)"""
        if self.user:  # Only logged in users earn points
            return int(self.subtotal * Decimal('0.02'))
        return 0

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
