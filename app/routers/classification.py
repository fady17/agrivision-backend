from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.gemini_service import gemini_service
from app.models.schemas import APIResponse

router = APIRouter()

@router.post("/analyze", response_model=APIResponse)
async def analyze_plant_disease(file: UploadFile = File(...)):
    """
    Production Endpoint: Upload -> Structured JSON Diagnosis
    """
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Invalid file type")
        
    try:
        contents = await file.read()
        
        # Call the new structured method
        analysis_result = await gemini_service.analyze_image_structured(contents)
        
        if not analysis_result.is_plant:
             return APIResponse(
                 status="error", 
                 error="The image does not appear to be a plant.",
                 data=analysis_result # Optional: return data to show why AI thought it wasn't a plant
             )

        return APIResponse(status="success", data=analysis_result)
        
    except ValueError as ve:
         raise HTTPException(status_code=500, detail=str(ve))
    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail="Internal analysis failed")