from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.gemini_service import gemini_service
from app.services.storage_service import storage_service  # Import Storage Service
from app.models.schemas import APIResponse

router = APIRouter()

@router.post("/analyze", response_model=APIResponse)
async def analyze_plant_disease(file: UploadFile = File(...)):
    """
    Full Pipeline: Upload -> MinIO -> Gemini -> JSON Result
    """
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Invalid file type")
        
    try:
        # 1. Read file content
        contents = await file.read()
        
        # 2. Upload to MinIO (Async/Blocking handling is managed by FastAPI threads)
        # We upload first so we have the URL even if AI fails (optional strategy)
        # or we can do it in parallel. For simplicity, sequential:
        upload_result = storage_service.upload_image(contents, file.content_type)
        image_url = upload_result["url"]
        
        # 3. Analyze with Gemini
        analysis_result = await gemini_service.analyze_image_structured(contents)
        
        # 4. Attach the URL to the result
        analysis_result.image_url = image_url
        
        # 5. Handle Non-Plant Logic
        if not analysis_result.is_plant:
             return APIResponse(
                 status="error", 
                 error="The image does not appear to be a plant.",
                 data=analysis_result
             )

        return APIResponse(status="success", data=analysis_result)
        
    except ValueError as ve:
         raise HTTPException(status_code=500, detail=str(ve))
    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail="Internal analysis failed")