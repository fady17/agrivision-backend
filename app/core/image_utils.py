import io
from PIL import Image

def optimize_image(image_bytes: bytes, max_size: int = 1024, quality: int = 85) -> bytes:
    """
    Resizes image to max_dimension keeping aspect ratio.
    Converts to standard JPEG.
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            # Convert RGBA to RGB (fix for PNGs)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Calculate new size maintaining aspect ratio
            img.thumbnail((max_size, max_size))
            
            # Save to bytes
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality)
            return output.getvalue()
    except Exception as e:
        # Fallback: return original if optimization fails
        print(f"Image optimization failed: {e}")
        return image_bytes