import hashlib
from typing import cast, Dict, Any

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.ai_providers import get_ai_provider
from app.services.storage_service import storage_service
from app.models.schemas import APIResponse, PlantAnalysisResult, Diagnosis, Severity
from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.scan import Scan
from app.core.image_utils import optimize_image
from app.core.exceptions import AIServiceError

router = APIRouter()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png"}


@router.post("/analyze", response_model=APIResponse)
async def analyze_plant_disease(
    file: UploadFile = File(...),
    language: str = Query(default="en", pattern="^(en|ar)$", description="Response language: 'en' or 'ar'"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Full Pipeline: Upload → MinIO → AI Provider → JSON Result

    The AI provider (Gemini / Ollama / LM Studio) is selected via the
    AI_PROVIDER environment variable — no code changes required to switch.

    Pass ?language=ar to receive all text fields in Arabic.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type. Accepted: JPEG, PNG")

    try:
        # 1. Read & optimise
        raw_contents = await file.read()
        optimized_contents = optimize_image(raw_contents)

        # 2. Deduplicate via SHA-256 hash
        img_hash = hashlib.sha256(optimized_contents).hexdigest()

        # 3. Cache lookup
        query = select(Scan).where(Scan.image_hash == img_hash).limit(1)
        result = await db.execute(query)
        existing_scan = result.scalars().first()

        if existing_scan:
            return _build_cached_response(existing_scan)

        # 4. Upload to MinIO
        upload_result = storage_service.upload_image(optimized_contents, "image/jpeg")
        image_url = upload_result["url"]

        # 5. AI analysis — provider-agnostic call
        ai_provider = get_ai_provider()
        analysis_result = await ai_provider.analyze_image_structured(optimized_contents, language=language)
        analysis_result.image_url = image_url

        # 6. Persist result
        new_scan = Scan(
            user_id=current_user.id,
            image_url=image_url,
            image_hash=img_hash,
            diagnosis_name=(
                analysis_result.diagnosis.name if analysis_result.is_plant else "Not a Plant"
            ),
            confidence=(
                analysis_result.diagnosis.confidence if analysis_result.is_plant else 1.0
            ),
            severity_score=(
                analysis_result.severity.score if analysis_result.is_plant else 0
            ),
            full_analysis=analysis_result.model_dump(mode="json"),
        )
        db.add(new_scan)
        await db.commit()

        # 7. Return
        if not analysis_result.is_plant:
            return APIResponse(
                status="error",
                error="The image does not appear to be a plant.",
                data=analysis_result,
            )

        return APIResponse(status="success", data=analysis_result)

    except AIServiceError as exc:
        # Known, descriptive failures from the AI layer
        raise HTTPException(status_code=502, detail=str(exc))

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    except Exception as exc:
        print(f"[analyze] Unexpected error: {exc}")
        raise HTTPException(status_code=500, detail="Internal analysis failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_cached_response(existing_scan: Scan) -> APIResponse:
    """
    Reconstruct an APIResponse from a cached Scan row.

    Note: cast() here is a typing hint only — the explicit float() / int()
    conversions are what actually coerce the SQLAlchemy column values at
    runtime.
    """
    full_analysis_data: Dict[str, Any] = (
        cast(Dict[str, Any], existing_scan.full_analysis) or {}
    )
    stored_diagnosis = full_analysis_data.get("diagnosis", {})
    stored_severity = full_analysis_data.get("severity", {})

    return APIResponse(
        status="success",
        data=PlantAnalysisResult(
            is_plant=True,
            image_url=str(existing_scan.image_url),
            diagnosis=Diagnosis(
                name=str(existing_scan.diagnosis_name),
                scientific_name=stored_diagnosis.get("scientific_name"),
                confidence=float(existing_scan.confidence),      # type: ignore[arg-type]
                description=stored_diagnosis.get("description", "Retrieved from cache."),
            ),
            severity=Severity(
                level=stored_severity.get("level", "Unknown"),
                score=int(existing_scan.severity_score),          # type: ignore[arg-type]
                visual_indicators=stored_severity.get("visual_indicators", []),
            ),
            recommendation=full_analysis_data.get(
                "recommendation", "See previous analysis."
            ),
        ),
    )
# import hashlib
# from typing import cast, Dict, Any

# from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select

# from app.services.ai_providers import get_ai_provider
# from app.services.storage_service import storage_service
# from app.models.schemas import APIResponse, PlantAnalysisResult, Diagnosis, Severity
# from app.core.deps import get_current_user
# from app.core.database import get_db
# from app.models.user import User
# from app.models.scan import Scan
# from app.core.image_utils import optimize_image
# from app.core.exceptions import AIServiceError

# router = APIRouter()

# ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png"}


# @router.post("/analyze", response_model=APIResponse)
# async def analyze_plant_disease(
#     file: UploadFile = File(...),
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
# ):
#     """
#     Full Pipeline: Upload → MinIO → AI Provider → JSON Result

#     The AI provider (Gemini / Ollama / LM Studio) is selected via the
#     AI_PROVIDER environment variable — no code changes required to switch.
#     """
#     if file.content_type not in ALLOWED_CONTENT_TYPES:
#         raise HTTPException(status_code=400, detail="Invalid file type. Accepted: JPEG, PNG")

#     try:
#         # 1. Read & optimise
#         raw_contents = await file.read()
#         optimized_contents = optimize_image(raw_contents)

#         # 2. Deduplicate via SHA-256 hash
#         img_hash = hashlib.sha256(optimized_contents).hexdigest()

#         # 3. Cache lookup
#         query = select(Scan).where(Scan.image_hash == img_hash).limit(1)
#         result = await db.execute(query)
#         existing_scan = result.scalars().first()

#         if existing_scan:
#             return _build_cached_response(existing_scan)

#         # 4. Upload to MinIO
#         upload_result = storage_service.upload_image(optimized_contents, "image/jpeg")
#         image_url = upload_result["url"]

#         # 5. AI analysis — provider-agnostic call
#         ai_provider = get_ai_provider()
#         analysis_result = await ai_provider.analyze_image_structured(optimized_contents)
#         analysis_result.image_url = image_url

#         # 6. Persist result
#         new_scan = Scan(
#             user_id=current_user.id,
#             image_url=image_url,
#             image_hash=img_hash,
#             diagnosis_name=(
#                 analysis_result.diagnosis.name if analysis_result.is_plant else "Not a Plant"
#             ),
#             confidence=(
#                 analysis_result.diagnosis.confidence if analysis_result.is_plant else 1.0
#             ),
#             severity_score=(
#                 analysis_result.severity.score if analysis_result.is_plant else 0
#             ),
#             full_analysis=analysis_result.model_dump(mode="json"),
#         )
#         db.add(new_scan)
#         await db.commit()

#         # 7. Return
#         if not analysis_result.is_plant:
#             return APIResponse(
#                 status="error",
#                 error="The image does not appear to be a plant.",
#                 data=analysis_result,
#             )

#         return APIResponse(status="success", data=analysis_result)

#     except AIServiceError as exc:
#         # Known, descriptive failures from the AI layer
#         raise HTTPException(status_code=502, detail=str(exc))

#     except ValueError as exc:
#         raise HTTPException(status_code=422, detail=str(exc))

#     except Exception as exc:
#         print(f"[analyze] Unexpected error: {exc}")
#         raise HTTPException(status_code=500, detail="Internal analysis failed")


# # ---------------------------------------------------------------------------
# # Helpers
# # ---------------------------------------------------------------------------

# def _build_cached_response(existing_scan: Scan) -> APIResponse:
#     """
#     Reconstruct an APIResponse from a cached Scan row.

#     Note: cast() here is a typing hint only — the explicit float() / int()
#     conversions are what actually coerce the SQLAlchemy column values at
#     runtime.
#     """
#     full_analysis_data: Dict[str, Any] = (
#         cast(Dict[str, Any], existing_scan.full_analysis) or {}
#     )
#     stored_diagnosis = full_analysis_data.get("diagnosis", {})
#     stored_severity = full_analysis_data.get("severity", {})

#     return APIResponse(
#         status="success",
#         data=PlantAnalysisResult(
#             is_plant=True,
#             image_url=str(existing_scan.image_url),
#             diagnosis=Diagnosis(
#                 name=str(existing_scan.diagnosis_name),
#                 scientific_name=stored_diagnosis.get("scientific_name"),
#                 confidence=float(existing_scan.confidence),      # type: ignore[arg-type]
#                 description=stored_diagnosis.get("description", "Retrieved from cache."),
#             ),
#             severity=Severity(
#                 level=stored_severity.get("level", "Unknown"),
#                 score=int(existing_scan.severity_score),          # type: ignore[arg-type]
#                 visual_indicators=stored_severity.get("visual_indicators", []),
#             ),
#             recommendation=full_analysis_data.get(
#                 "recommendation", "See previous analysis."
#             ),
#         ),
#     )
# # import hashlib
# # from typing import cast, Dict, Any # <--- Import typing helpers
# # from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
# # from sqlalchemy.ext.asyncio import AsyncSession
# # from sqlalchemy import select

# # from app.services.gemini_service import gemini_service
# # from app.services.storage_service import storage_service
# # from app.models.schemas import APIResponse, PlantAnalysisResult, Diagnosis, Severity
# # from app.core.deps import get_current_user
# # from app.core.database import get_db
# # from app.models.user import User
# # from app.models.scan import Scan
# # from app.core.image_utils import optimize_image

# # router = APIRouter()

# # @router.post("/analyze", response_model=APIResponse)
# # async def analyze_plant_disease(
# #     file: UploadFile = File(...),
# #     current_user: User = Depends(get_current_user),
# #     db: AsyncSession = Depends(get_db)
# # ):
# #     """
# #     Full Pipeline: Upload -> MinIO -> Gemini -> JSON Result
# #     """
# #     if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
# #         raise HTTPException(status_code=400, detail="Invalid file type")
        
# #     try:
# #         # 1. Read file content
# #         raw_contents = await file.read()
        
# #         # 2. OPTIMIZATION: Resize before anything else
# #         optimized_contents = optimize_image(raw_contents)
        
# #         # 3. Calculate Hash
# #         img_hash = hashlib.sha256(optimized_contents).hexdigest()
        
# #         # 4. Check Cache
# #         query = select(Scan).where(Scan.image_hash == img_hash).limit(1)
# #         result = await db.execute(query)
# #         existing_scan = result.scalars().first()
        
# #         if existing_scan:
# #             # CACHE HIT!
            
           
# #             full_analysis_data = cast(Dict[str, Any], existing_scan.full_analysis) or {}
# #             stored_diagnosis = full_analysis_data.get('diagnosis', {})
            
# #             return APIResponse(
# #                 status="success", 
# #                 data=PlantAnalysisResult(
# #                     is_plant=True,
# #                     # Cast columns to native types
# #                     image_url=str(existing_scan.image_url),
                    
# #                     diagnosis=Diagnosis(
# #                         name=str(existing_scan.diagnosis_name),
# #                         scientific_name=stored_diagnosis.get('scientific_name'),
# #                         # Cast confidence column to float
# #                         confidence=float(cast(float, existing_scan.confidence)),
# #                         description=stored_diagnosis.get('description', "Retrieved from cache.")
# #                     ),
                    
# #                     severity=Severity(
# #                         level="Unknown", 
# #                         # Cast severity column to int
# #                         score=int(cast(int, existing_scan.severity_score)),
# #                         visual_indicators=[] 
# #                     ),
                    
# #                     recommendation=full_analysis_data.get('recommendation', "See previous analysis.")
# #                 )
# #             )

# #         # 5. Cache Miss - Upload to MinIO
# #         upload_result = storage_service.upload_image(optimized_contents, "image/jpeg")
# #         image_url = upload_result["url"]
        
# #         # 6. Analyze with Gemini
# #         analysis_result = await gemini_service.analyze_image_structured(optimized_contents)
# #         analysis_result.image_url = image_url

# #         # 7. Save to Database
# #         new_scan = Scan(
# #             user_id=current_user.id,
# #             image_url=image_url,
# #             diagnosis_name=analysis_result.diagnosis.name if analysis_result.is_plant else "Not a Plant",
# #             confidence=analysis_result.diagnosis.confidence if analysis_result.is_plant else 1.0,
# #             severity_score=analysis_result.severity.score if analysis_result.is_plant else 0,
            
# #             # Pass full_analysis and image_hash as separate arguments
# #             full_analysis=analysis_result.model_dump(mode='json'), 
# #             image_hash=img_hash 
# #         )
        
# #         db.add(new_scan)
# #         await db.commit()
        
# #         if not analysis_result.is_plant:
# #              return APIResponse(
# #                  status="error", 
# #                  error="The image does not appear to be a plant.",
# #                  data=analysis_result
# #              )

# #         return APIResponse(status="success", data=analysis_result)
        
# #     except ValueError as ve:
# #          raise HTTPException(status_code=500, detail=str(ve))
# #     except Exception as e:
# #         print(f"Server Error: {e}")
# #         raise HTTPException(status_code=500, detail="Internal analysis failed")