"""
LM Studio provider using the OpenAI Python SDK.

LM Studio exposes a fully OpenAI-compatible API at /v1, so we use
the official SDK directly. Structured output via json_schema means
the model is grammar-constrained — it cannot produce malformed JSON
or skip required fields.

Recommended vision-capable models:
  - qwen/qwen2.5-vl-7b-instruct  (strong multilingual + vision)
  - llava-v1.6-mistral-7b-q4_k_m
  - moondream2
"""

import base64
import json
from typing import Optional

from openai import AsyncOpenAI, APIConnectionError, APIStatusError, APITimeoutError
from openai.types.chat import ChatCompletionMessageParam
from pydantic import ValidationError

from app.core.exceptions import AIServiceError
from app.models.schemas import PlantAnalysisResult
from app.services.ai_providers.base import AIProvider


PLANT_ANALYSIS_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "plant_analysis_result",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "is_plant": {
                    "type": "boolean",
                    "description": "True if the image contains a plant."
                },
                "diagnosis": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "scientific_name": {"type": ["string", "null"]},
                        "confidence": {"type": "number"},
                        "description": {"type": "string"}
                    },
                    "required": ["name", "scientific_name", "confidence", "description"]
                },
                "severity": {
                    "type": "object",
                    "properties": {
                        "level": {
                            "type": "string",
                            "enum": ["Healthy", "Low", "Medium", "High", "Critical"]
                        },
                        "score": {"type": "integer"},
                        "visual_indicators": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["level", "score", "visual_indicators"]
                },
                "recommendation": {"type": "string"}
            },
            "required": ["is_plant", "diagnosis", "severity", "recommendation"]
        }
    }
}


class LMStudioProvider(AIProvider):
    """
    LM Studio local inference using the OpenAI-compatible /v1 API.

    Setup:
      1. Open LM Studio → Developer tab → Start Server (default: localhost:1234)
      2. Load a vision-capable model in the UI
      3. Set LM_STUDIO_MODEL in .env to the model identifier shown in LM Studio
    """

    def __init__(
        self,
        model_name: str,
        base_url: str = "http://localhost:1234/v1",
        timeout: float = 380.0,
        api_key: Optional[str] = "lm-studio",
    ):
        self.model_name = model_name
        self.timeout = timeout
        # AsyncOpenAI is fully async — no thread pool needed
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key or "lm-studio",
            timeout=timeout,
            max_retries=2,
        )

    # @staticmethod
    # def _encode_image(image_bytes: bytes) -> str:
    #     b64 = base64.b64encode(image_bytes).decode("utf-8")
    #     return f"data:image/jpeg;base64,{b64}"

    @staticmethod
    def _encode_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        return f"data:{mime_type};base64,{b64}"
    
    async def analyze_image_structured(
        self, image_bytes: bytes, language: str = "en", mime_type: str = "image/jpeg"
    ) -> PlantAnalysisResult:
        image_url = self._encode_image(image_bytes, mime_type)

        messages: list[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": self._get_system_prompt(language),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url},
                    },
                    {
                        "type": "text",
                        "text": "Analyse this plant image and return the structured JSON result.",
                    },
                ],
            },
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format=PLANT_ANALYSIS_SCHEMA, # type: ignore
                # Low temperature for deterministic JSON output
                # Disable thinking — the reasoning chain breaks JSON parsing
                # Source: Qwen3.5 best practices (instruct mode, precise tasks)
                temperature=0.6,
                top_p=0.95,
                presence_penalty=0.0,
                extra_body={
                    "top_k": 20,
                    "min_p": 0.0,
                    "chat_template_kwargs": {"enable_thinking": False},
                },
            )

            raw_content = response.choices[0].message.content or ""
            json_data = json.loads(raw_content)
            return PlantAnalysisResult(**json_data)

        except APITimeoutError as exc:
            raise AIServiceError(
                f"[LMStudio] Request timed out after {self.timeout}s. "
                "Try a smaller/faster model or increase LOCAL_AI_TIMEOUT."
            ) from exc

        except APIConnectionError as exc:
            raise AIServiceError(
                f"[LMStudio] Cannot reach server. Is LM Studio running with a model loaded? ({exc})"
            ) from exc

        except APIStatusError as exc:
            raise AIServiceError(
                f"[LMStudio] Server returned HTTP {exc.status_code}: {exc.message}"
            ) from exc

        except json.JSONDecodeError as exc:
            raise AIServiceError(f"[LMStudio] Model returned invalid JSON: {exc}") from exc
        except ValidationError as exc:
            raise AIServiceError(f"[LMStudio] Model JSON didn't match schema: {exc}") from exc
        except (KeyError, TypeError) as exc:
            raise AIServiceError(f"[LMStudio] Unexpected model output structure: {exc}") from exc

        except AIServiceError:
            raise

        except Exception as exc:
            raise AIServiceError(f"[LMStudio] Unexpected error: {exc}") from exc