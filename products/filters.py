import django_filters
from django.db.models import Q
from .models import Product, Category

class ProductFilter(django_filters.FilterSet):
    """Filter set for Product model"""
    
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.filter(is_active=True),
        field_name='category'
    )
    
    price_min = django_filters.NumberFilter(
        field_name='price',
        lookup_expr='gte'
    )
    
    price_max = django_filters.NumberFilter(
        field_name='price',
        lookup_expr='lte'
    )
    
    rating_min = django_filters.NumberFilter(
        field_name='rating',
        lookup_expr='gte'
    )
    
    is_new = django_filters.BooleanFilter(
        field_name='is_new'
    )
    
    is_popular = django_filters.BooleanFilter(
        field_name='is_popular'
    )
    
    is_trending = django_filters.BooleanFilter(
        field_name='is_trending'
    )
    
    is_best_seller = django_filters.BooleanFilter(
        field_name='is_best_seller'
    )
    
    colors = django_filters.CharFilter(
        method='filter_colors'
    )
    
    sizes = django_filters.CharFilter(
        method='filter_sizes'
    )
    
    class Meta:
        model = Product
        fields = ['category', 'is_new', 'is_popular', 'is_trending', 'is_best_seller']
    
    def filter_colors(self, queryset, name, value):
        """Filter products by available colors"""
        if value:
            colors = [color.strip() for color in value.split(',')]
            query = Q()
            for color in colors:
                query |= Q(colors__icontains=color)
            return queryset.filter(query)
        return queryset
    
    def filter_sizes(self, queryset, name, value):
        """Filter products by available sizes"""
        if value:
            sizes = [size.strip() for size in value.split(',')]
            query = Q()
            for size in sizes:
                query |= Q(sizes__icontains=size)
            return queryset.filter(query)
        return queryset
