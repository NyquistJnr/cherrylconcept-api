from rest_framework import status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import  IsAuthenticatedOrReadOnly,IsAdminUser
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .pagination import ProductPagination 
from django.db.models import Q
from django.shortcuts import get_object_or_404
from .models import Category, Product, FeaturedCollection, HomePageFeaturedProducts
from .serializers import (
    CategorySerializer, 
    ProductListSerializer, 
    ProductDetailSerializer, 
    ProductCreateUpdateSerializer,
    FeaturedCollectionSerializer,
    FeaturedCollectionUpdateSerializer,
    HomePageFeaturedProductsSerializer,
    HomePageFeaturedProductsUpdateSerializer,
)
from .utils import CloudinaryManager
from .filters import ProductFilter

# Category Views
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def category_list_create(request):
    """List all categories or create a new category"""
    if request.method == 'GET':
        categories = Category.objects.filter(is_active=True)
        serializer = CategorySerializer(categories, many=True)
        return Response({
            'message': 'Categories retrieved successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            category = serializer.save()
            return Response({
                'message': 'Category created successfully',
                'data': CategorySerializer(category).data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'message': 'Category creation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticatedOrReadOnly])
def category_detail(request, category_id):
    """Retrieve, update or delete a category"""
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'GET':
        serializer = CategorySerializer(category)
        return Response({
            'message': 'Category retrieved successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        serializer = CategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            category = serializer.save()
            return Response({
                'message': 'Category updated successfully',
                'data': CategorySerializer(category).data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'message': 'Category update failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        if category.products.exists():
            return Response({
                'message': 'Cannot delete category with existing products'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        category.delete()
        return Response({
            'message': 'Category deleted successfully'
        }, status=status.HTTP_200_OK)

# Product Views
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def product_list_create(request):
    """List all products with filtering or create a new product"""
    if request.method == 'GET':
        products = Product.objects.filter(is_active=True).select_related('category').prefetch_related('images')
        
        filterset = ProductFilter(request.GET, queryset=products)
        products = filterset.qs
        
        search = request.GET.get('search')
        if search:
            products = products.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(category__name__icontains=search)
            )
        
        ordering = request.GET.get('ordering', '-created_at')
        if ordering in ['price', '-price', 'name', '-name', 'rating', '-rating', 'created_at', '-created_at']:
            products = products.order_by(ordering)
        
       
        paginator = ProductPagination()
        paginated_products = paginator.paginate_queryset(products, request)
        serializer = ProductListSerializer(paginated_products, many=True)
        return paginator.get_paginated_response(serializer.data)
      

    elif request.method == 'POST':
        serializer = ProductCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                product = serializer.save()
                return Response({
                    'message': 'Product created successfully',
                    'data': ProductDetailSerializer(product).data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({
                    'message': 'Product creation failed',
                    'error': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'message': 'Product creation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticatedOrReadOnly])
def product_detail(request, product_id):
    """Retrieve, update or delete a product"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'GET':
        serializer = ProductDetailSerializer(product)
        return Response({
            'message': 'Product retrieved successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        serializer = ProductCreateUpdateSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            try:
                product = serializer.save()
                return Response({
                    'message': 'Product updated successfully',
                    'data': ProductDetailSerializer(product).data
                }, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({
                    'message': 'Product update failed',
                    'error': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'message': 'Product update failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        try:
            cloudinary_manager = CloudinaryManager()
            public_ids = [img.public_id for img in product.images.all()]
            if public_ids:
                cloudinary_manager.delete_multiple_images(public_ids)
            
            product.delete()
            
            return Response({
                'message': 'Product deleted successfully'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'message': 'Product deletion failed',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def products_by_category(request, category_id):
    """Get all products in a specific category"""
    category = get_object_or_404(Category, id=category_id, is_active=True)
    products = Product.objects.filter(category=category, is_active=True).select_related('category').prefetch_related('images')
    
    filterset = ProductFilter(request.GET, queryset=products)
    products = filterset.qs
    
    search = request.GET.get('search')
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    ordering = request.GET.get('ordering', '-created_at')
    if ordering in ['price', '-price', 'name', '-name', 'rating', '-rating', 'created_at', '-created_at']:
        products = products.order_by(ordering)
    
 
    request.custom_message = f'Products in {category.name} retrieved successfully'

    paginator = ProductPagination()
    paginated_products = paginator.paginate_queryset(products, request)
    serializer = ProductListSerializer(paginated_products, many=True)
    
    # Get the response and add extra category data to it
    response = paginator.get_paginated_response(serializer.data)
    response.data['data']['category'] = CategorySerializer(category).data
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def recent_featured_products(request):
    """Get recent featured products from all categories (trending, popular, new, best sellers)"""
    from django.utils import timezone
    from datetime import timedelta
    
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    trending_products = Product.objects.filter(
        is_trending=True, 
        is_active=True
    ).select_related('category').prefetch_related('images').order_by('-created_at')[:1]
    
    popular_products = Product.objects.filter(
        is_popular=True, 
        is_active=True
    ).select_related('category').prefetch_related('images').order_by('-created_at')[:1]
    
    new_products = Product.objects.filter(
        is_new=True, 
        is_active=True
    ).select_related('category').prefetch_related('images').order_by('-created_at')[:1]
    
    best_seller_products = Product.objects.filter(
        is_best_seller=True, 
        is_active=True
    ).select_related('category').prefetch_related('images').order_by('-created_at')[:1]
    
    return Response({
        'message': 'Recent featured products retrieved successfully',
        'data': {
            'trending': ProductListSerializer(trending_products, many=True).data,
            'popular': ProductListSerializer(popular_products, many=True).data,
            'new': ProductListSerializer(new_products, many=True).data,
            'best_sellers': ProductListSerializer(best_seller_products, many=True).data
        },
        'counts': {
            'trending': trending_products.count(),
            'popular': popular_products.count(),
            'new': new_products.count(),
            'best_sellers': best_seller_products.count()
        }
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def featured_products(request):
    """Get featured products (popular, new, trending, and best seller products)"""
    popular_products = Product.objects.filter(is_popular=True, is_active=True).select_related('category').prefetch_related('images')[:8]
    new_products = Product.objects.filter(is_new=True, is_active=True).select_related('category').prefetch_related('images')[:8]
    trending_products = Product.objects.filter(is_trending=True, is_active=True).select_related('category').prefetch_related('images')[:8]
    best_seller_products = Product.objects.filter(is_best_seller=True, is_active=True).select_related('category').prefetch_related('images')[:8]
    
    return Response({
        'message': 'Featured products retrieved successfully',
        'data': {
            'popular': ProductListSerializer(popular_products, many=True).data,
            'new': ProductListSerializer(new_products, many=True).data,
            'trending': ProductListSerializer(trending_products, many=True).data,
            'best_sellers': ProductListSerializer(best_seller_products, many=True).data
        }
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def trending_products(request):
    """Get trending products"""
    products = Product.objects.filter(is_trending=True, is_active=True).select_related('category').prefetch_related('images')
    
    filterset = ProductFilter(request.GET, queryset=products)
    products = filterset.qs
    
    search = request.GET.get('search')
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(category__name__icontains=search)
        )
    
    ordering = request.GET.get('ordering', '-created_at')
    if ordering in ['price', '-price', 'name', '-name', 'rating', '-rating', 'created_at', '-created_at']:
        products = products.order_by(ordering)
    

    request.custom_message = 'Trending products retrieved successfully'
    paginator = ProductPagination()
    paginated_products = paginator.paginate_queryset(products, request)
    serializer = ProductListSerializer(paginated_products, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def best_seller_products(request):
    """Get best seller products"""
    products = Product.objects.filter(is_best_seller=True, is_active=True).select_related('category').prefetch_related('images')
    
    filterset = ProductFilter(request.GET, queryset=products)
    products = filterset.qs
    
    search = request.GET.get('search')
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(category__name__icontains=search)
        )
    
    ordering = request.GET.get('ordering', '-created_at')
    if ordering in ['price', '-price', 'name', '-name', 'rating', '-rating', 'created_at', '-created_at']:
        products = products.order_by(ordering)
    
    request.custom_message = 'Best seller products retrieved successfully'
    paginator = ProductPagination()
    paginated_products = paginator.paginate_queryset(products, request)
    serializer = ProductListSerializer(paginated_products, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def feature_collections_view(request):
    """
    GET: Retrieve the 3 featured collections for the homepage.
    POST: (Admin only) Create or update the featured collections.
    """
    if request.method == 'GET':
        collections = FeaturedCollection.objects.all()
        serializer = FeaturedCollectionSerializer(collections, many=True)
        return Response({
            'message': 'Featured collections retrieved successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    if request.method == 'POST':
        if not request.user.is_staff:
            return Response({'error': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
        
        # Expecting a list of 3 collection objects
        serializer = FeaturedCollectionUpdateSerializer(data=request.data, many=True)
        if serializer.is_valid():
            for collection_data in serializer.validated_data:
                collection_type = collection_data.get('collection_type')
                FeaturedCollection.objects.update_or_create(
                    collection_type=collection_type,
                    defaults=collection_data
                )
            return Response({'message': 'Featured collections updated successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def home_featured_products_view(request):
    """
    GET: Retrieve the 4 featured products for the homepage.
    POST: (Admin only) Set or update the 4 featured products.
    """
    # Use get_or_create for the singleton model
    featured_products_instance, created = HomePageFeaturedProducts.objects.get_or_create(pk=1)

    if request.method == 'GET':
        serializer = HomePageFeaturedProductsSerializer(featured_products_instance)
        # We want a flat list of products, not a nested object
        products_list = [product for product in serializer.data.values() if product is not None]
        return Response({
            'message': 'Home page featured products retrieved successfully',
            'data': products_list
        }, status=status.HTTP_200_OK)

    if request.method == 'POST':
        if not request.user.is_staff:
            return Response({'error': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = HomePageFeaturedProductsUpdateSerializer(
            instance=featured_products_instance,
            data=request.data
        )
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Home page featured products updated successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
