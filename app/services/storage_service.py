import uuid
import io
from minio import Minio
from datetime import timedelta
from urllib.parse import urlparse
from app.core.config import settings

class StorageService:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket = settings.MINIO_BUCKET_NAME

    def upload_image(self, file_data: bytes, content_type: str) -> dict:
        """
        Uploads bytes to MinIO and returns metadata + presigned URL.
        """
        # 1. Generate unique filename (UUID)
        ext = ".jpg" if "jpeg" in content_type else ".png"
        image_id = str(uuid.uuid4())
        filename = f"{image_id}{ext}"
        
        # 2. Prepare stream
        file_stream = io.BytesIO(file_data)
        file_size = len(file_data)

        # 3. Upload to MinIO
        self.client.put_object(
            bucket_name=self.bucket,
            object_name=filename,
            data=file_stream,
            length=file_size,
            content_type=content_type
        )

        # 4. Generate Presigned URL (Valid for 1 hour)
        # This allows the frontend to display the image even if the bucket is private
        url = self.client.get_presigned_url(
            "GET",
            self.bucket,
            filename,
            expires=timedelta(hours=1)
        )

        return {
            "image_id": image_id,
            "filename": filename,
            "url": url,
            "size": file_size
        }
    
    def get_fresh_url(self, expired_url: str) -> str:
        """
        Extracts filename from an old URL and generates a new presigned URL.
        """
        try:
            # 1. Parse the URL to get the path
            parsed = urlparse(expired_url)
            path_parts = parsed.path.split('/')
            
            # 2. Extract object name (last part of path)
            # URL is usually /bucket_name/filename.jpg
            if not path_parts:
                return expired_url
                
            object_name = path_parts[-1]
            
            # 3. Generate new signed URL (valid for 1 hour from NOW)
            return self.client.get_presigned_url(
                "GET",
                self.bucket,
                object_name,
                expires=timedelta(hours=1)
            )
        except Exception as e:
            print(f"Failed to refresh URL: {e}")
            return expired_url

# Singleton instance
storage_service = StorageService()