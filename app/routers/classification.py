from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.gemini_service import gemini_service

router = APIRouter()

@router.post("/test-gemini")
async def test_gemini_integration(file: UploadFile = File(...)):
    """
    Phase 3 Test Endpoint: Direct image upload -> Gemini Analysis
    """
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Invalid file type")
        
    try:
        contents = await file.read()
        response_text = await gemini_service.analyze_image_raw(contents)
        
        return {
            "status": "success",
            "ai_response": response_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Analysis Failed: {str(e)}")