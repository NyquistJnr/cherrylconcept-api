from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Category, Product, ProductImage

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ['image_preview', 'public_id']
    fields = ['image', 'image_preview', 'is_main', 'alt_text', 'order', 'public_id']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 100px; height: 100px; object-fit: cover;" />',
                obj.image.url
            )
        return "No Image"
    image_preview.short_description = 'Preview'

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'products_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    
    def products_count(self, obj):
        return obj.products.count()
    products_count.short_description = 'Products'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'price', 'original_price', 'discount_percentage', 
        'rating', 'reviews_count', 'is_new', 'is_popular', 'is_trending', 
        'is_best_seller', 'is_active', 'main_image_preview'
    ]
    list_filter = ['category', 'is_new', 'is_popular', 'is_trending', 'is_best_seller', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'category__name']
    readonly_fields = ['created_at', 'updated_at', 'discount_percentage']
    inlines = [ProductImageInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'description', 'video_url')
        }),
        ('Pricing', {
            'fields': ('price', 'original_price', 'discount_percentage')
        }),
        ('Product Details', {
            'fields': ('colors', 'sizes', 'features', 'specifications')
        }),
        ('Ratings & Reviews', {
            'fields': ('rating', 'reviews_count')
        }),
        ('Status Flags', {
            'fields': ('is_new', 'is_popular', 'is_trending', 'is_best_seller', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def main_image_preview(self, obj):
        if obj.main_image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover;" />',
                obj.main_image
            )
        return "No Image"
    main_image_preview.short_description = 'Image'
    
    def discount_percentage(self, obj):
        discount = obj.discount_percentage
        if discount > 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">{}%</span>',
                discount
            )
        return "No Discount"
    discount_percentage.short_description = 'Discount'

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'image_preview', 'is_main', 'order', 'created_at']
    list_filter = ['is_main', 'created_at']
    search_fields = ['product__name', 'alt_text']
    readonly_fields = ['image_preview', 'public_id']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 100px; height: 100px; object-fit: cover;" />',
                obj.image.url
            )
        return "No Image"
    image_preview.short_description = 'Preview'
