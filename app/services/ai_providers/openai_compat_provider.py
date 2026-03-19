# import base64
# import json
# from typing import Optional

# import httpx

# from app.core.exceptions import AIServiceError
# from app.models.schemas import PlantAnalysisResult
# from app.services.ai_providers.base import AIProvider


# class OpenAICompatibleProvider(AIProvider):
#     """
#     Shared implementation for any backend that exposes an
#     OpenAI-compatible /v1/chat/completions endpoint with vision support.

#     Both Ollama (>=0.1.34) and LM Studio (>=0.2.x) qualify.
#     """

#     def __init__(
#         self,
#         base_url: str,
#         model_name: str,
#         provider_label: str,
#         timeout: float = 120.0,
#         api_key: Optional[str] = None,   # LM Studio may need a dummy key
#     ):
#         self.base_url = base_url.rstrip("/")
#         self.model_name = model_name
#         self.provider_label = provider_label   # used in log messages
#         self.timeout = timeout

#         # Build headers — some servers require an Authorization header even if
#         # the actual value doesn't matter (LM Studio accepts anything).
#         self.headers = {"Content-Type": "application/json"}
#         if api_key:
#             self.headers["Authorization"] = f"Bearer {api_key}"

#     # ------------------------------------------------------------------
#     # Internal helpers
#     # ------------------------------------------------------------------

#     @staticmethod
#     def _encode_image(image_bytes: bytes) -> str:
#         """Return a base64-encoded JPEG data-URI string."""
#         b64 = base64.b64encode(image_bytes).decode("utf-8")
#         return f"data:image/jpeg;base64,{b64}"

#     def _build_payload(self, image_bytes: bytes) -> dict:
#         """
#         Construct the /v1/chat/completions request body.

#         The image is sent as a vision message following the OpenAI multimodal
#         format, which both Ollama and LM Studio understand.
#         """
#         image_url = self._encode_image(image_bytes)

#         return {
#             "model": self.model_name,
#             "messages": [
#                 {
#                     "role": "system",
#                     "content": self._get_system_prompt(),
#                 },
#                 {
#                     "role": "user",
#                     "content": [
#                         {
#                             "type": "image_url",
#                             "image_url": {"url": image_url},
#                         },
#                         {
#                             "type": "text",
#                             "text": "Analyse this plant image and return the JSON result.",
#                         },
#                     ],
#                 },
#             ],
#             # Ask for JSON — honoured by most local models when the system
#             # prompt is explicit; some servers also support response_format.
#             "response_format": {"type": "json_object"},
#             "temperature": 0.1,   # Low temp = more deterministic JSON output
#             "stream": False,
#         }

#     @staticmethod
#     def _extract_text(response_json: dict) -> str:
#         """Pull the assistant message content out of a chat completion."""
#         try:
#             return response_json["choices"][0]["message"]["content"]
#         except (KeyError, IndexError) as exc:
#             raise AIServiceError(
#                 f"Unexpected response shape from provider: {response_json}"
#             ) from exc

#     @staticmethod
#     def _strip_fences(text: str) -> str:
#         """
#         Some models wrap JSON in ```json … ``` even when told not to.
#         Strip those fences defensively before parsing.
#         """
#         text = text.strip()
#         if text.startswith("```"):
#             lines = text.splitlines()
#             # Drop first line (```json or ```) and last line (```)
#             text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
#         return text.strip()

#     # ------------------------------------------------------------------
#     # Public interface
#     # ------------------------------------------------------------------

#     async def analyze_image_structured(self, image_bytes: bytes) -> PlantAnalysisResult:
#         payload = self._build_payload(image_bytes)
#         endpoint = f"{self.base_url}/v1/chat/completions"

#         try:
#             async with httpx.AsyncClient(timeout=self.timeout) as client:
#                 response = await client.post(
#                     endpoint,
#                     headers=self.headers,
#                     json=payload,
#                 )

#             if response.status_code != 200:
#                 raise AIServiceError(
#                     f"[{self.provider_label}] HTTP {response.status_code}: {response.text}"
#                 )

#             raw_text = self._extract_text(response.json())
#             clean_text = self._strip_fences(raw_text)
#             json_data = json.loads(clean_text)
#             return PlantAnalysisResult(**json_data)

#         except httpx.ConnectError as exc:
#             raise AIServiceError(
#                 f"[{self.provider_label}] Cannot reach server at {self.base_url}. "
#                 "Is it running?"
#             ) from exc

#         except httpx.TimeoutException as exc:
#             raise AIServiceError(
#                 f"[{self.provider_label}] Request timed out after {self.timeout}s. "
#                 "Try a smaller/faster model."
#             ) from exc

#         except (json.JSONDecodeError, KeyError, TypeError) as exc:
#             raise AIServiceError(
#                 f"[{self.provider_label}] Failed to parse model output: {exc}"
#             ) from exc

#         except AIServiceError:
#             raise   # already well-described

#         except Exception as exc:
#             raise AIServiceError(
#                 f"[{self.provider_label}] Unexpected error: {exc}"
#             ) from exc