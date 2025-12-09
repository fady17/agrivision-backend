import google.generativeai as genai
from PIL import Image
import io
from app.core.config import settings

class GeminiService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY) # type: ignore
        self.model = genai.GenerativeModel("gemini-2.5-flash") # type: ignore

    async def analyze_image_raw(self, image_bytes: bytes) -> str:
        """
        Sends image to Gemini and returns raw text response.
        Used for Phase 3 connectivity testing.
        """
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_bytes))
            
            prompt = "Analyze this image. If it is a plant, describe its condition. If not, say 'Not a plant'."
            
            # Generate content
            response = self.model.generate_content([prompt, image])
            return response.text
            
        except Exception as e:
            print(f"Gemini Error: {e}")
            raise e

gemini_service = GeminiService()