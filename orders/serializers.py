from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from decimal import Decimal
from .models import Order, OrderItem, LoyaltyAccount, LoyaltyTransaction, ShippingAddress
from products.models import Product

User = get_user_model()

class OrderItemCreateSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    color = serializers.CharField(max_length=50, required=False, allow_blank=True)
    size = serializers.CharField(max_length=20, required=False, allow_blank=True)
    
    def validate_product_id(self, value):
        try:
            product = Product.objects.get(id=value, is_active=True)
            return value
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found or inactive")

class OrderCreateSerializer(serializers.Serializer):
    # Customer Information
    customer_email = serializers.EmailField()
    customer_first_name = serializers.CharField(max_length=100)
    customer_last_name = serializers.CharField(max_length=100)
    customer_phone = serializers.CharField(max_length=20)
    
    # Shipping Information
    shipping_address_line1 = serializers.CharField(max_length=255)
    shipping_address_line2 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    shipping_city = serializers.CharField(max_length=100)
    shipping_state = serializers.CharField(max_length=100)
    shipping_postal_code = serializers.CharField(max_length=20)
    shipping_country = serializers.CharField(max_length=100)
    
    # Order Items
    items = OrderItemCreateSerializer(many=True)
    
    # Optional loyalty points usage (for logged in users)
    use_loyalty_points = serializers.IntegerField(min_value=0, required=False, default=0)
    
    # Optional: Save shipping address for logged in users
    save_shipping_address = serializers.BooleanField(required=False, default=False)
    shipping_address_label = serializers.CharField(max_length=50, required=False, allow_blank=True)
    
    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required")
        return value
    
    def validate_use_loyalty_points(self, value):
        request = self.context.get('request')
        if value > 0 and not request.user.is_authenticated:
            raise serializers.ValidationError("Only logged in users can use loyalty points")
        
        if value > 0 and request.user.is_authenticated:
            try:
                loyalty_account = request.user.loyalty_account
                if value > loyalty_account.current_balance:
                    raise serializers.ValidationError(f"Insufficient loyalty points. Available: {loyalty_account.current_balance}")
            except LoyaltyAccount.DoesNotExist:
                raise serializers.ValidationError("No loyalty account found")
        
        return value
    
    def validate(self, attrs):
        # Validate products exist and calculate totals
        total_amount = Decimal('0.00')
        
        for item_data in attrs['items']:
            try:
                product = Product.objects.get(id=item_data['product_id'], is_active=True)
                item_total = product.price * item_data['quantity']
                total_amount += item_total
            except Product.DoesNotExist:
                raise serializers.ValidationError(f"Product {item_data['product_id']} not found")
        
        attrs['calculated_subtotal'] = total_amount
        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request.user.is_authenticated else None
        
        items_data = validated_data.pop('items')
        use_loyalty_points = validated_data.pop('use_loyalty_points', 0)
        save_shipping_address = validated_data.pop('save_shipping_address', False)
        shipping_address_label = validated_data.pop('shipping_address_label', '')
        calculated_subtotal = validated_data.pop('calculated_subtotal')
        
        # Calculate order totals
        subtotal = calculated_subtotal
        shipping_fee = self.calculate_shipping_fee(subtotal)
        tax_amount = self.calculate_tax(subtotal)
        loyalty_discount = Decimal(str(use_loyalty_points))  # 1 point = $1 discount
        total_amount = subtotal + shipping_fee + tax_amount - loyalty_discount
        
        # Create order
        order = Order.objects.create(
            user=user,
            customer_email=validated_data['customer_email'],
            customer_first_name=validated_data['customer_first_name'],
            customer_last_name=validated_data['customer_last_name'],
            customer_phone=validated_data['customer_phone'],
            shipping_address_line1=validated_data['shipping_address_line1'],
            shipping_address_line2=validated_data.get('shipping_address_line2', ''),
            shipping_city=validated_data['shipping_city'],
            shipping_state=validated_data['shipping_state'],
            shipping_postal_code=validated_data['shipping_postal_code'],
            shipping_country=validated_data['shipping_country'],
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            tax_amount=tax_amount,
            total_amount=total_amount,
            loyalty_points_used=use_loyalty_points,
            currency='NGN',  # Default currency
            status='pending',  # Order starts as pending payment
            payment_status='pending'
        )
        
        # Create order items
        for item_data in items_data:
            product = Product.objects.get(id=item_data['product_id'])
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                product_price=product.price,
                quantity=item_data['quantity'],
                color=item_data.get('color', ''),
                size=item_data.get('size', ''),
            )
        
        # Handle loyalty points for logged in users (deduct used points immediately)
        if user and use_loyalty_points > 0:
            loyalty_account, created = LoyaltyAccount.objects.get_or_create(user=user)
            loyalty_account.use_points(use_loyalty_points, order)
        
        # Save shipping address if requested
        if user and save_shipping_address and shipping_address_label:
            ShippingAddress.objects.create(
                user=user,
                label=shipping_address_label,
                first_name=validated_data['customer_first_name'],
                last_name=validated_data['customer_last_name'],
                phone_number=validated_data['customer_phone'],
                address_line1=validated_data['shipping_address_line1'],
                address_line2=validated_data.get('shipping_address_line2', ''),
                city=validated_data['shipping_city'],
                state=validated_data['shipping_state'],
                postal_code=validated_data['shipping_postal_code'],
                country=validated_data['shipping_country'],
            )
        
        return order
    
    def calculate_shipping_fee(self, subtotal):
        """Calculate shipping fee - free shipping over $100"""
        if subtotal >= Decimal('100.00'):
            return Decimal('0.00')
        return Decimal('10.00')
    
    def calculate_tax(self, subtotal):
        """Calculate tax - 8% tax rate"""
        return subtotal * Decimal('0.08')

class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(source='product.id', read_only=True)
    product_image = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_id', 'product_name', 'product_price', 'quantity', 
            'color', 'size', 'line_total', 'product_image'
        ]
    
    def get_product_image(self, obj):
        return obj.product.main_image if obj.product else None

class OrderListSerializer(serializers.ModelSerializer):
    customer_full_name = serializers.ReadOnlyField()
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer_full_name', 'total_amount', 
            'status', 'items_count', 'created_at'
        ]
    
    def get_items_count(self, obj):
        return obj.items.count()

class OrderDetailSerializer(serializers.ModelSerializer):
    customer_full_name = serializers.ReadOnlyField()
    shipping_address = serializers.ReadOnlyField()
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user', 'customer_email', 'customer_first_name',
            'customer_last_name', 'customer_phone', 'customer_full_name',
            'shipping_address_line1', 'shipping_address_line2', 'shipping_city',
            'shipping_state', 'shipping_postal_code', 'shipping_country', 'shipping_address',
            'subtotal', 'shipping_fee', 'tax_amount', 'total_amount', 'currency',
            'status', 'payment_status', 'payment_reference', 'payment_method', 'paid_amount',
            'payment_date', 'notes', 'tracking_number', 'loyalty_points_earned', 
            'loyalty_points_used', 'items', 'created_at', 'updated_at', 'confirmed_at', 
            'shipped_at', 'delivered_at'
        ]

class LoyaltyTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyTransaction
        fields = ['id', 'transaction_type', 'points', 'description', 'created_at']

class LoyaltyAccountSerializer(serializers.ModelSerializer):
    recent_transactions = LoyaltyTransactionSerializer(source='transactions', many=True, read_only=True)
    
    class Meta:
        model = LoyaltyAccount
        fields = [
            'id', 'total_points_earned', 'total_points_used', 'current_balance', 
            'tier', 'created_at', 'recent_transactions'
        ]

class ShippingAddressSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    formatted_address = serializers.ReadOnlyField()
    
    class Meta:
        model = ShippingAddress
        fields = [
            'id', 'label', 'first_name', 'last_name', 'full_name', 'phone_number',
            'address_line1', 'address_line2', 'city', 'state', 'postal_code', 
            'country', 'formatted_address', 'is_default', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)
