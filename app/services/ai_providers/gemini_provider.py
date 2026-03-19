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