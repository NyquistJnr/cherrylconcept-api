import cloudinary
import cloudinary.uploader
import cloudinary.api
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class CloudinaryManager:
    """Utility class for managing Cloudinary operations"""
    
    def __init__(self):
        # Ensure Cloudinary is configured
        if not cloudinary.config().cloud_name:
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET,
                secure=True
            )
    
    def upload_image(self, image_file, folder="products", **kwargs):
        """
        Upload image to Cloudinary
        
        Args:
            image_file: Django UploadedFile object
            folder: Cloudinary folder name
            **kwargs: Additional Cloudinary upload options
        
        Returns:
            dict: Cloudinary upload response
        """
        try:
            # Default upload options
            upload_options = {
                'folder': folder,
                'resource_type': 'image',
                'format': 'webp',  # Convert to WebP for better performance
                'quality': 'auto:good',
                'fetch_format': 'auto',
                'responsive': True,
                'width': 1200,
                'height': 1200,
                'crop': 'limit'
            }
            
            # Update with any additional options
            upload_options.update(kwargs)
            
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(image_file, **upload_options)
            
            logger.info(f"Image uploaded successfully: {result.get('public_id')}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to upload image to Cloudinary: {str(e)}")
            raise Exception(f"Image upload failed: {str(e)}")
    
    def delete_image(self, public_id):
        """
        Delete image from Cloudinary
        
        Args:
            public_id: Cloudinary public ID of the image
        
        Returns:
            dict: Cloudinary deletion response
        """
        try:
            if not public_id:
                return {'deleted': []}
                
            result = cloudinary.uploader.destroy(public_id)
            logger.info(f"Image deleted successfully: {public_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to delete image from Cloudinary: {str(e)}")
            # Don't raise exception for deletion failures
            return {'deleted': []}
    
    def delete_multiple_images(self, public_ids):
        """
        Delete multiple images from Cloudinary
        
        Args:
            public_ids: List of Cloudinary public IDs
        
        Returns:
            dict: Cloudinary deletion response
        """
        try:
            if not public_ids:
                return {'deleted': []}
            
            # Filter out empty public_ids
            valid_public_ids = [pid for pid in public_ids if pid]
            
            if not valid_public_ids:
                return {'deleted': []}
            
            result = cloudinary.api.delete_resources(valid_public_ids)
            logger.info(f"Multiple images deleted: {len(valid_public_ids)} images")
            return result
        except Exception as e:
            logger.error(f"Failed to delete multiple images: {str(e)}")
            # Don't raise exception for deletion failures
            return {'deleted': []}
    
    def get_image_url(self, public_id, transformation=None):
        """
        Get optimized image URL from Cloudinary
        
        Args:
            public_id: Cloudinary public ID
            transformation: Dictionary of transformation options
        
        Returns:
            str: Optimized image URL
        """
        try:
            if transformation:
                return cloudinary.CloudinaryImage(public_id).build_url(**transformation)
            else:
                return cloudinary.CloudinaryImage(public_id).build_url(
                    format='auto',
                    quality='auto:good'
                )
        except Exception as e:
            logger.error(f"Failed to generate image URL: {str(e)}")
            return None
    
    def create_thumbnail(self, public_id, width=300, height=300):
        """
        Create thumbnail URL for an image
        
        Args:
            public_id: Cloudinary public ID
            width: Thumbnail width
            height: Thumbnail height
        
        Returns:
            str: Thumbnail URL
        """
        return self.get_image_url(public_id, {
            'width': width,
            'height': height,
            'crop': 'fill',
            'gravity': 'center',
            'format': 'auto',
            'quality': 'auto:good'
        })
