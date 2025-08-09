from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Order, LoyaltyAccount, ShippingAddress
from .serializers import (
    OrderCreateSerializer, 
    OrderListSerializer, 
    OrderDetailSerializer,
    LoyaltyAccountSerializer,
    ShippingAddressSerializer
)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_order(request):
    """Create new order - works for both logged in and guest users"""
    serializer = OrderCreateSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        try:
            order = serializer.save()
            return Response({
                'message': 'Order created successfully',
                'data': OrderDetailSerializer(order).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({
                'message': 'Order creation failed',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({
        'message': 'Order creation failed',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_orders(request):
    """Get orders for logged in user"""
    orders = Order.objects.filter(user=request.user).select_related().prefetch_related('items')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    serializer = OrderListSerializer(orders, many=True)
    return Response({
        'message': 'Orders retrieved successfully',
        'data': serializer.data,
        'count': orders.count()
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def order_detail(request, order_id):
    """Get order details - accessible by order owner or guest with order number"""
    try:
        if request.user.is_authenticated:
            # For logged in users, check if they own the order
            order = get_object_or_404(Order, Q(id=order_id) & (Q(user=request.user) | Q(user__isnull=True)))
        else:
            # For guest users, only show orders without user association
            order = get_object_or_404(Order, id=order_id, user__isnull=True)
        
        serializer = OrderDetailSerializer(order)
        return Response({
            'message': 'Order retrieved successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    except Order.DoesNotExist:
        return Response({
            'message': 'Order not found'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([AllowAny])
def order_by_number(request, order_number):
    """Get order by order number - for order tracking"""
    email = request.GET.get('email')
    
    try:
        order = Order.objects.get(order_number=order_number)
        
        # If user is authenticated and owns the order, allow access
        if request.user.is_authenticated and order.user == request.user:
            pass
        # If email is provided and matches, allow access
        elif email and order.customer_email.lower() == email.lower():
            pass
        else:
            return Response({
                'message': 'Order not found or email does not match'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = OrderDetailSerializer(order)
        return Response({
            'message': 'Order retrieved successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    except Order.DoesNotExist:
        return Response({
            'message': 'Order not found'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_order_status(request, order_id):
    """Update order status - admin only (you can add admin check)"""
    order = get_object_or_404(Order, id=order_id)
    
    new_status = request.data.get('status')
    tracking_number = request.data.get('tracking_number', '')
    notes = request.data.get('notes', '')
    
    if new_status not in dict(Order.STATUS_CHOICES):
        return Response({
            'message': 'Invalid status'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    order.status = new_status
    if tracking_number:
        order.tracking_number = tracking_number
    if notes:
        order.notes = notes
    
    # Update timestamps based on status
    from django.utils import timezone
    if new_status == 'confirmed' and not order.confirmed_at:
        order.confirmed_at = timezone.now()
    elif new_status == 'shipped' and not order.shipped_at:
        order.shipped_at = timezone.now()
    elif new_status == 'delivered' and not order.delivered_at:
        order.delivered_at = timezone.now()
    
    order.save()
    
    return Response({
        'message': 'Order status updated successfully',
        'data': OrderDetailSerializer(order).data
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def loyalty_account(request):
    """Get user's loyalty account details"""
    loyalty_account, created = LoyaltyAccount.objects.get_or_create(user=request.user)
    
    # Get recent transactions (last 10)
    recent_transactions = loyalty_account.transactions.all()[:10]
    
    serializer = LoyaltyAccountSerializer(loyalty_account)
    return Response({
        'message': 'Loyalty account retrieved successfully',
        'data': serializer.data
    }, status=status.HTTP_200_OK)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def shipping_addresses(request):
    """Get user's shipping addresses or create new one"""
    if request.method == 'GET':
        addresses = ShippingAddress.objects.filter(user=request.user)
        serializer = ShippingAddressSerializer(addresses, many=True)
        return Response({
            'message': 'Shipping addresses retrieved successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        serializer = ShippingAddressSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            address = serializer.save()
            return Response({
                'message': 'Shipping address created successfully',
                'data': ShippingAddressSerializer(address).data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'message': 'Shipping address creation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def shipping_address_detail(request, address_id):
    """Get, update or delete shipping address"""
    address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
    
    if request.method == 'GET':
        serializer = ShippingAddressSerializer(address)
        return Response({
            'message': 'Shipping address retrieved successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        serializer = ShippingAddressSerializer(address, data=request.data, partial=True)
        if serializer.is_valid():
            address = serializer.save()
            return Response({
                'message': 'Shipping address updated successfully',
                'data': ShippingAddressSerializer(address).data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'message': 'Shipping address update failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        address.delete()
        return Response({
            'message': 'Shipping address deleted successfully'
        }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_default_address(request, address_id):
    """Set shipping address as default"""
    address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
    
    # Unset all other default addresses
    ShippingAddress.objects.filter(user=request.user).update(is_default=False)
    
    # Set this address as default
    address.is_default = True
    address.save()
    
    return Response({
        'message': 'Default shipping address updated successfully',
        'data': ShippingAddressSerializer(address).data
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def order_summary(request):
    """Calculate order summary for cart items"""
    items = request.data.get('items', [])
    use_loyalty_points = int(request.data.get('use_loyalty_points', 0))
    
    if not items:
        return Response({
            'message': 'No items provided'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from decimal import Decimal
        from products.models import Product
        
        subtotal = Decimal('0.00')
        order_items = []
        
        # Calculate subtotal
        for item_data in items:
            product = Product.objects.get(id=item_data['product_id'], is_active=True)
            quantity = int(item_data['quantity'])
            line_total = product.price * quantity
            subtotal += line_total
            
            order_items.append({
                'product_id': str(product.id),
                'product_name': product.name,
                'product_price': str(product.price),
                'quantity': quantity,
                'line_total': str(line_total),
                'product_image': product.main_image
            })
        
        # Calculate fees
        shipping_fee = Decimal('10000.00') if subtotal < Decimal('100000.00') else Decimal('0.00')
        tax_amount = subtotal * Decimal('0.03')
        loyalty_discount = Decimal(str(use_loyalty_points))
        total_amount = subtotal + shipping_fee + tax_amount - loyalty_discount
        
        # Calculate potential loyalty points for logged in users
        potential_points = 0
        if request.user.is_authenticated:
            potential_points = int(subtotal * Decimal('0.05'))

        free_shipping_threshold = Decimal('100000.00')
        
        return Response({
            'message': 'Order summary calculated successfully',
            'data': {
                'items': order_items,
                'subtotal': str(subtotal),
                'shipping_fee': str(shipping_fee),
                'tax_amount': str(tax_amount), 
                'loyalty_discount': str(loyalty_discount),
                'total_amount': str(total_amount),
                'potential_loyalty_points': potential_points,
                'free_shipping_threshold': str(free_shipping_threshold),
                'free_shipping_remaining': str(max(Decimal('0.00'), free_shipping_threshold - subtotal))
        }
    }, status=status.HTTP_200_OK)

    except Product.DoesNotExist:
        return Response({
            'message': 'One or more products not found'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'message': 'Error calculating order summary',
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([AllowAny])
def order_stats(request):
    """Get order statistics"""
    from django.db.models import Count, Sum
    
    stats = {
        'total_orders': Order.objects.count(),
        'orders_by_status': dict(Order.objects.values('status').annotate(count=Count('id')).values_list('status', 'count')),
    }
    
    if request.user.is_authenticated:
        user_stats = {
            'user_total_orders': Order.objects.filter(user=request.user).count(),
            'user_total_spent': Order.objects.filter(user=request.user).aggregate(total=Sum('total_amount'))['total'] or 0,
        }
        stats.update(user_stats)
    
    return Response({
        'message': 'Order statistics retrieved successfully',
        'data': stats
    }, status=status.HTTP_200_OK)
