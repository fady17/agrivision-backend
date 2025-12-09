import hashlib
from typing import cast, Dict, Any # <--- Import typing helpers
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.gemini_service import gemini_service
from app.services.storage_service import storage_service
from app.models.schemas import APIResponse, PlantAnalysisResult, Diagnosis, Severity
from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.scan import Scan
from app.core.image_utils import optimize_image

router = APIRouter()

@router.post("/analyze", response_model=APIResponse)
async def analyze_plant_disease(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Full Pipeline: Upload -> MinIO -> Gemini -> JSON Result
    """
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Invalid file type")
        
    try:
        # 1. Read file content
        raw_contents = await file.read()
        
        # 2. OPTIMIZATION: Resize before anything else
        optimized_contents = optimize_image(raw_contents)
        
        # 3. Calculate Hash
        img_hash = hashlib.sha256(optimized_contents).hexdigest()
        
        # 4. Check Cache
        query = select(Scan).where(Scan.image_hash == img_hash).limit(1)
        result = await db.execute(query)
        existing_scan = result.scalars().first()
        
        if existing_scan:
            # CACHE HIT!
            
            # TYPE FIX: We cast the SQLAlchemy attribute to Dict[str, Any] so Pylance stays happy.
            # At runtime, existing_scan.full_analysis IS ALREADY a dict.
            full_analysis_data = cast(Dict[str, Any], existing_scan.full_analysis) or {}
            stored_diagnosis = full_analysis_data.get('diagnosis', {})
            
            return APIResponse(
                status="success", 
                data=PlantAnalysisResult(
                    is_plant=True,
                    # Cast columns to native types
                    image_url=str(existing_scan.image_url),
                    
                    diagnosis=Diagnosis(
                        name=str(existing_scan.diagnosis_name),
                        scientific_name=stored_diagnosis.get('scientific_name'),
                        # Cast confidence column to float
                        confidence=float(cast(float, existing_scan.confidence)),
                        description=stored_diagnosis.get('description', "Retrieved from cache.")
                    ),
                    
                    severity=Severity(
                        level="Unknown", 
                        # Cast severity column to int
                        score=int(cast(int, existing_scan.severity_score)),
                        visual_indicators=[] 
                    ),
                    
                    recommendation=full_analysis_data.get('recommendation', "See previous analysis.")
                )
            )

        # 5. Cache Miss - Upload to MinIO
        upload_result = storage_service.upload_image(optimized_contents, "image/jpeg")
        image_url = upload_result["url"]
        
        # 6. Analyze with Gemini
        analysis_result = await gemini_service.analyze_image_structured(optimized_contents)
        analysis_result.image_url = image_url

        # 7. Save to Database
        new_scan = Scan(
            user_id=current_user.id,
            image_url=image_url,
            diagnosis_name=analysis_result.diagnosis.name if analysis_result.is_plant else "Not a Plant",
            confidence=analysis_result.diagnosis.confidence if analysis_result.is_plant else 1.0,
            severity_score=analysis_result.severity.score if analysis_result.is_plant else 0,
            
            # Pass full_analysis and image_hash as separate arguments
            full_analysis=analysis_result.model_dump(mode='json'), 
            image_hash=img_hash 
        )
        
        db.add(new_scan)
        await db.commit()
        
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