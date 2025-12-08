import sys
import os
from minio import Minio
from minio.error import S3Error

# Add project root to python path so we can import app.core
sys.path.append(os.getcwd())

from app.core.config import settings

def init_storage():
    print(f"Connecting to MinIO at {settings.MINIO_ENDPOINT}...")
    
    # Note: When running this script locally (outside Docker), 
    # you might need to change MINIO_ENDPOINT to localhost:9000 
    # if not using Docker networking.
    
    client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE
    )

    try:
        if not client.bucket_exists(settings.MINIO_BUCKET_NAME):
            print(f"Creating bucket: {settings.MINIO_BUCKET_NAME}")
            client.make_bucket(settings.MINIO_BUCKET_NAME)
        else:
            print(f"Bucket '{settings.MINIO_BUCKET_NAME}' already exists.")
            
    except S3Error as err:
        print(f"MinIO Error: {err}")
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    init_storage()