import io
import json

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from PIL import Image
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.exceptions import AIServiceError
from app.models.schemas import PlantAnalysisResult
from app.services.ai_providers.base import AIProvider


class GeminiProvider(AIProvider):
    """
    Google Gemini vision provider.
    Uses native google-generativeai SDK with JSON mode enabled.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        genai.configure(api_key=api_key)  # type: ignore[attr-defined]
        self.model = genai.GenerativeModel(  # type: ignore[attr-defined]
            model_name,
            generation_config={"response_mime_type": "application/json"},
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (google_exceptions.GoogleAPICallError, google_exceptions.RetryError)
        ),
    )
    async def analyze_image_structured(self, image_bytes: bytes, language: str = "en") -> PlantAnalysisResult:
        try:
            image = Image.open(io.BytesIO(image_bytes))
            response = self.model.generate_content([self._get_system_prompt(language), image])
            json_data = json.loads(response.text)
            return PlantAnalysisResult(**json_data)

        except (
            google_exceptions.GoogleAPICallError,
            google_exceptions.RetryError,
        ) as e:
            # Retryable — bubble up so tenacity can catch it
            print(f"[Gemini] Transient error: {e}")
            raise

        except Exception as e:
            # Non-retryable (bad JSON, corrupt image, etc.)
            print(f"[Gemini] Permanent error: {e}")
            raise AIServiceError(f"Gemini analysis failed: {e}") from e
# import google.generativeai as genai
# from PIL import Image
# import io
# import json
# from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type # <--- NEW
# from google.api_core import exceptions as google_exceptions

# from app.core.config import settings
# from app.models.schemas import PlantAnalysisResult
# from app.core.exceptions import AIServiceError

# class GeminiService:
#     def __init__(self):
#         genai.configure(api_key=settings.GEMINI_API_KEY) # type: ignore
#         # Enable JSON mode specifically
#         self.model = genai.GenerativeModel( # type: ignore
#             "gemini-2.5-flash",
#             generation_config={"response_mime_type": "application/json"}
#         )

#     def _get_system_prompt(self):
#         return """
#         You are an expert plant pathologist AI (AgriVision). Analyze the uploaded image.
        
#         Strictly output JSON matching this structure:
#         {
#             "is_plant": boolean,
#             "diagnosis": {
#                 "name": "string",
#                 "scientific_name": "string or null",
#                 "confidence": float (0-1),
#                 "description": "string"
#             },
#             "severity": {
#                 "level": "Healthy" | "Low" | "Medium" | "High" | "Critical",
#                 "score": int (0-100),
#                 "visual_indicators": ["string", "string"]
#             },
#             "recommendation": "string"
#         }

#         Rules:
#         1. If the image is NOT a plant, set "is_plant": false and fill other fields with null/generic data.
#         2. Severity Score: 0 is perfect health, 100 is dead.
#         3. Be concise and actionable.
#         """

#     @retry(
#         stop=stop_after_attempt(3), # Try 3 times
#         wait=wait_exponential(multiplier=1, min=2, max=10), # Wait 2s, then 4s, etc.
#         retry=retry_if_exception_type((google_exceptions.GoogleAPICallError, google_exceptions.RetryError))
#     )
#     async def analyze_image_structured(self, image_bytes: bytes) -> PlantAnalysisResult:
#         try:
#             image = Image.open(io.BytesIO(image_bytes))
            
#             # Send prompt + image
#             response = self.model.generate_content([self._get_system_prompt(), image])
            
#             # Parse JSON
#             json_data = json.loads(response.text)
            
#             # Validate with Pydantic
#             return PlantAnalysisResult(**json_data)
            
#         except (google_exceptions.GoogleAPICallError, google_exceptions.RetryError) as e:
#                 # This triggers the @retry decorator
#                 print(f"Gemini Transient Error: {e}")
#                 raise e 
#         except Exception as e:
#             # This is a permanent error (e.g. Bad JSON, Invalid Image) -> Don't retry
#             print(f"Gemini Permanent Error: {e}")
#             raise AIServiceError(f"AI Analysis Failed: {str(e)}")

# gemini_service = GeminiService()