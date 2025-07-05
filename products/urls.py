from django.urls import path
from . import views

urlpatterns = [
    # Category endpoints
    path('categories/', views.category_list_create, name='category_list_create'),
    path('categories/<uuid:category_id>/', views.category_detail, name='category_detail'),
    
    # Product endpoints
    path('', views.product_list_create, name='product_list_create'),
    path('<uuid:product_id>/', views.product_detail, name='product_detail'),
    path('category/<uuid:category_id>/', views.products_by_category, name='products_by_category'),
    path('featured/', views.featured_products, name='featured_products'),
    path('trending/', views.trending_products, name='trending_products'),
    path('best-sellers/', views.best_seller_products, name='best_seller_products'),
    path('recent-featured/', views.recent_featured_products, name='recent_featured_products'),
]
