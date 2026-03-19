# """
# Thin provider wrappers for Ollama and LM Studio.

# Both delegate all logic to OpenAICompatibleProvider — they just set
# sensible defaults for their respective servers and document the
# model name expectations clearly.

# Recommended vision-capable models:
#   Ollama   : llava, llava-llama3, moondream, bakllava
#   LM Studio: any GGUF model with vision support (e.g. llava-v1.6-mistral-7b)

# Usage in .env:
#   AI_PROVIDER=ollama
#   OLLAMA_BASE_URL=http://localhost:11434
#   OLLAMA_MODEL=llava-llama3

#   AI_PROVIDER=lmstudio
#   LM_STUDIO_BASE_URL=http://localhost:1234
#   LM_STUDIO_MODEL=llava-v1.6-mistral-7b-q4
# """

# from typing import Optional
# from app.services.ai_providers.openai_compat_provider import OpenAICompatibleProvider


# class OllamaProvider(OpenAICompatibleProvider):
#     """
#     Ollama local inference server.

#     Ollama exposes an OpenAI-compatible API at /v1/chat/completions
#     when started with `OLLAMA_HOST=0.0.0.0 ollama serve`.

#     No API key is required — pass None (default).
#     """

#     def __init__(
#         self,
#         model_name: str = "llava-llama3",
#         base_url: str = "http://localhost:11434",
#         timeout: float = 180.0,   # Local models are slower; give them more time
#     ):
#         super().__init__(
#             base_url=base_url,
#             model_name=model_name,
#             provider_label="Ollama",
#             timeout=timeout,
#             api_key=None,
#         )


# class LMStudioProvider(OpenAICompatibleProvider):
#     """
#     LM Studio local inference server.

#     LM Studio's server is enabled via the Local Server tab in the UI.
#     It listens on http://localhost:1234 by default and requires the
#     model to already be loaded in the UI before requests are sent.

#     LM Studio technically accepts any string as an API key (or none),
#     but some setups require the Authorization header to be present.
#     """

#     def __init__(
#         self,
#         model_name: str,
#         base_url: str = "http://localhost:1234",
#         timeout: float = 180.0,
#         api_key: Optional[str] = "lm-studio",  # Dummy key — LM Studio ignores it
#     ):
#         super().__init__(
#             base_url=base_url,
#             model_name=model_name,
#             provider_label="LMStudio",
#             timeout=timeout,
#             api_key=api_key,
#         )