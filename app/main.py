from fastapi import FastAPI, Response, status
from minio import Minio
from app.core.config import settings
from app.routers import upload, classification, auth, history
from sqlalchemy import text # Import text
from app.core.database import get_db
from fastapi import Depends
from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.exceptions import AIServiceError, StorageError, ImageValidationError # Import custom exceptions

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION
)


# --- GLOBAL EXCEPTION HANDLERS ---

@app.exception_handler(AIServiceError)
async def ai_exception_handler(request: Request, exc: AIServiceError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "error",
            "code": "AI_SERVICE_UNAVAILABLE",
            "message": "The AI engine is currently overloaded. Please try again in a moment.",
            "detail": str(exc)
        },
    )

@app.exception_handler(StorageError)
async def storage_exception_handler(request: Request, exc: StorageError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "error",
            "code": "STORAGE_ERROR",
            "message": "Image upload failed. Please check your connection.",
            "detail": str(exc)
        },
    )

@app.exception_handler(ImageValidationError)
async def validation_exception_handler(request: Request, exc: ImageValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "status": "error",
            "code": "INVALID_IMAGE",
            "message": "The image file appears corrupted or unsupported.",
            "detail": str(exc)
        },
    )
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"]) 
# Include the router
app.include_router(upload.router, prefix="/api/v1", tags=["Image Operations"])
# Add the new router
app.include_router(classification.router, prefix="/api/v1", tags=["AI Classification"])
app.include_router(history.router, prefix="/api/v1", tags=["User History"]) 
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
async def health_check(
    response: Response, 
    db_session = Depends(get_db) # Inject DB session
):
    health_status = {
        "api": "online",
        "storage": "unknown", 
        "database": "unknown" # NEW
    }
    
    # 1. Check Storage (Existing)
    try:
        if minio_client.bucket_exists(settings.MINIO_BUCKET_NAME):
            health_status["storage"] = "connected"
        else:
            health_status["storage"] = "bucket_missing"
    except Exception:
        health_status["storage"] = "disconnected"

    # 2. Check Database (NEW)
    try:
        # Run a simple query "SELECT 1"
        await db_session.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = "disconnected"
        health_status["db_error"] = str(e)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return health_status
