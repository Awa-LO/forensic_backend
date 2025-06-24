from PIL import Image
import os
from django.conf import settings

def generate_thumbnail(image_path):
    try:
        img = Image.open(image_path)
        img.thumbnail(settings.THUMBNAIL_SIZE)
        
        thumb_path = os.path.join(
            settings.THUMBNAIL_ROOT, 
            os.path.basename(image_path)
        )
        img.save(thumb_path)
        return thumb_path
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        return None