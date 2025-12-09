import google.generativeai as genai
from PIL import Image
import io
import json
from app.core.config import settings
from app.models.schemas import PlantAnalysisResult

class GeminiService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY) # type: ignore
        # Enable JSON mode specifically
        self.model = genai.GenerativeModel( # type: ignore
            "gemini-2.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )

    def _get_system_prompt(self):
        return """
        You are an expert plant pathologist AI (AgriVision). Analyze the uploaded image.
        
        Strictly output JSON matching this structure:
        {
            "is_plant": boolean,
            "diagnosis": {
                "name": "string",
                "scientific_name": "string or null",
                "confidence": float (0-1),
                "description": "string"
            },
            "severity": {
                "level": "Healthy" | "Low" | "Medium" | "High" | "Critical",
                "score": int (0-100),
                "visual_indicators": ["string", "string"]
            },
            "recommendation": "string"
        }

        Rules:
        1. If the image is NOT a plant, set "is_plant": false and fill other fields with null/generic data.
        2. Severity Score: 0 is perfect health, 100 is dead.
        3. Be concise and actionable.
        """

    async def analyze_image_structured(self, image_bytes: bytes) -> PlantAnalysisResult:
        try:
            image = Image.open(io.BytesIO(image_bytes))
            
            # Send prompt + image
            response = self.model.generate_content([self._get_system_prompt(), image])
            
            # Parse JSON
            json_data = json.loads(response.text)
            
            # Validate with Pydantic
            return PlantAnalysisResult(**json_data)
            
        except Exception as e:
            print(f"Gemini Analysis Error: {e}")
            raise ValueError("Failed to analyze plant image")

gemini_service = GeminiService()