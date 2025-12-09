from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.services.storage_service import storage_service
from app.models.schemas import ImageUploadResult

router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

@router.post("/upload", response_model=ImageUploadResult)
async def upload_image(file: UploadFile = File(...)):
    # 1. Validate Content Type
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid file type. Only JPEG and PNG are allowed."
        )

    # 2. Read File
    try:
        contents = await file.read()
    except Exception:
        raise HTTPException(status_code=500, detail="Could not read file")

    # 3. Validate Size
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 10MB."
        )

    # 4. Upload via Service
    try:
        result = storage_service.upload_image(contents, file.content_type)
        
        return ImageUploadResult(
            image_id=result["image_id"],
            filename=result["filename"],
            url=result["url"],
            content_type=file.content_type,
            size=result["size"]
        )
    except Exception as e:
        # Log error in production
        print(f"Upload Error: {e}")
        raise HTTPException(status_code=500, detail="Storage upload failed")