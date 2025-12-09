from fastapi import FastAPI, Response, status
from minio import Minio
from app.core.config import settings
from app.routers import upload

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION
)

# Include the router
app.include_router(upload.router, prefix="/api/v1", tags=["Image Operations"])

# Global MinIO Client
minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE
)

@app.get("/")
def root():
    return {"message": "AgriVision API is running", "system": "healthy"}

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check(response: Response):
    """
    Verifies connection to MinIO storage.
    """
    health_status = {
        "api": "online",
        "storage": "unknown",
        "bucket": settings.MINIO_BUCKET_NAME
    }
    
    try:
        # Check if bucket exists to verify connection
        if minio_client.bucket_exists(settings.MINIO_BUCKET_NAME):
            health_status["storage"] = "connected"
        else:
            health_status["storage"] = "bucket_missing"
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            
    except Exception as e:
        health_status["storage"] = "disconnected"
        health_status["error"] = str(e)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return health_status