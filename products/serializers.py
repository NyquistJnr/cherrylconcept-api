from rest_framework import serializers
from django.utils.text import slugify
from .models import Category, Product, ProductImage
from .utils import CloudinaryManager

class CategorySerializer(serializers.ModelSerializer):
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'is_active', 'products_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']
    
    def get_products_count(self, obj):
        return obj.products.filter(is_active=True).count()
    
    def create(self, validated_data):
        validated_data['slug'] = slugify(validated_data['name'])
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        if 'name' in validated_data:
            validated_data['slug'] = slugify(validated_data['name'])
        return super().update(instance, validated_data)

class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductImage
        fields = ['id', 'image_url', 'public_id', 'is_main', 'alt_text', 'order']
        read_only_fields = ['id', 'public_id']
    
    def get_image_url(self, obj):
        return obj.image.url if obj.image else None

class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    main_image = serializers.SerializerMethodField()
    discount_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'price', 'original_price', 'category_name', 
            'main_image', 'colors', 'sizes', 'rating', 'reviews_count', 
            'is_new', 'is_popular', 'is_trending', 'is_best_seller', 
            'discount_percentage', 'created_at'
        ]
    
    def get_main_image(self, obj):
        return obj.main_image

class ProductDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    main_image = serializers.SerializerMethodField()
    all_image_urls = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'price', 'original_price', 'category', 'category_name',
            'colors', 'sizes', 'rating', 'reviews_count', 'is_new', 'is_popular',
            'is_trending', 'is_best_seller', 'description', 'video_url', 'features', 
            'specifications', 'main_image', 'images', 'all_image_urls', 
            'discount_percentage', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_main_image(self, obj):
        return obj.main_image

class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = Product
        fields = [
            'name', 'price', 'original_price', 'category', 'colors', 'sizes',
            'rating', 'reviews_count', 'is_new', 'is_popular', 'is_trending',
            'is_best_seller', 'description', 'video_url', 'features', 
            'specifications', 'is_active', 'images'
        ]
    
    def validate(self, attrs):
        # Ensure original_price is greater than or equal to price
        if attrs.get('original_price') and attrs.get('price'):
            if attrs['original_price'] < attrs['price']:
                raise serializers.ValidationError("Original price must be greater than or equal to current price")
        return attrs
    
    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        product = Product.objects.create(**validated_data)
        
        # Upload images to Cloudinary
        cloudinary_manager = CloudinaryManager()
        for index, image in enumerate(images_data):
            result = cloudinary_manager.upload_image(image, folder='products')
            ProductImage.objects.create(
                product=product,
                image=result['secure_url'],
                public_id=result['public_id'],
                is_main=(index == 0),  # First image is main
                order=index
            )
        
        return product
    
    def update(self, instance, validated_data):
        images_data = validated_data.pop('images', None)
        
        # Update product fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Handle image updates if provided
        if images_data is not None:
            cloudinary_manager = CloudinaryManager()
            
            # Delete existing images from Cloudinary
            for existing_image in instance.images.all():
                cloudinary_manager.delete_image(existing_image.public_id)
            
            # Delete existing image records
            instance.images.all().delete()
            
            # Upload new images
            for index, image in enumerate(images_data):
                result = cloudinary_manager.upload_image(image, folder='products')
                ProductImage.objects.create(
                    product=instance,
                    image=result['secure_url'],
                    public_id=result['public_id'],
                    is_main=(index == 0),
                    order=index
                )
        
        return instance
