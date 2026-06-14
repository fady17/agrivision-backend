
"""
Provider factory.

Reads AI_PROVIDER from settings and returns the correct AIProvider
implementation. The rest of the application only ever calls
    get_ai_provider()
and never imports a concrete provider directly.

Supported values for AI_PROVIDER:
    gemini     — Google Gemini (cloud, default)
    ollama     — Ollama local server
    lmstudio   — LM Studio local server
"""

from functools import lru_cache

from app.core.config import settings
from app.core.exceptions import AIServiceError
from app.services.ai_providers.base import AIProvider


@lru_cache(maxsize=1)
def get_ai_provider() -> AIProvider:
    """
    Return a cached singleton provider instance.

    The cache is intentional: providers are stateless (or hold only
    configuration), so one instance per process is correct and avoids
    repeated SDK initialisation on every request.
    """
    provider_name = settings.AI_PROVIDER.lower().strip()

    if provider_name == "gemini":
        from app.services.ai_providers.gemini_provider import GeminiProvider

        if not settings.GEMINI_API_KEY:
            raise AIServiceError(
                "AI_PROVIDER is 'gemini' but GEMINI_API_KEY is not set."
            )
        return GeminiProvider(
            api_key=settings.GEMINI_API_KEY,
            model_name=settings.GEMINI_MODEL,
        )

    # if provider_name == "ollama":
    #     from app.services.ai_providers.local_providers import OllamaProvider

    #     return OllamaProvider(
    #         base_url=settings.OLLAMA_BASE_URL,
    #         model_name=settings.OLLAMA_MODEL,
    #         timeout=settings.LOCAL_AI_TIMEOUT,
    #     )

    if provider_name == "lmstudio":
        from app.services.ai_providers.lmstudio_provider import LMStudioProvider

        return LMStudioProvider(
            base_url=settings.LM_STUDIO_BASE_URL,
            model_name=settings.LM_STUDIO_MODEL,
            timeout=settings.LOCAL_AI_TIMEOUT,
        )

    raise AIServiceError(
        f"Unknown AI_PROVIDER '{provider_name}'. "
        "Valid options: gemini | ollama | lmstudio"
    )
