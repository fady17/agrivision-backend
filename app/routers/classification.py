from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.gemini_service import gemini_service
from app.services.storage_service import storage_service  # Import Storage Service
from app.models.schemas import APIResponse
from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.scan import Scan

router = APIRouter()

@router.post("/analyze", response_model=APIResponse)
async def analyze_plant_disease(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user), # <--- Protect Route
    db: AsyncSession = Depends(get_db)              # <--- Inject DB
):
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

        # 5. Save to Database (Persistence)
        # Only save if it's actually a plant, or save everything depending on preference.
        # Let's save everything so users see "Non-plant" errors too.
        new_scan = Scan(
            user_id=current_user.id,
            image_url=image_url,
            diagnosis_name=analysis_result.diagnosis.name if analysis_result.is_plant else "Not a Plant",
            confidence=analysis_result.diagnosis.confidence if analysis_result.is_plant else 1.0,
            severity_score=analysis_result.severity.score if analysis_result.is_plant else 0,
            full_analysis=analysis_result.model_dump(mode='json')
        )
        
        db.add(new_scan)
        await db.commit()
        
        
        # 6. Handle Non-Plant Logic
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