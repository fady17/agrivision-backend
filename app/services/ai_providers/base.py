from abc import ABC, abstractmethod
from app.models.schemas import PlantAnalysisResult

SUPPORTED_LANGUAGES = {"en", "ar"}

_LANGUAGE_INSTRUCTIONS = {
    "en": "Write all text field values in English.",
    "ar": (
        "اكتب جميع قيم حقول النص باللغة العربية. "
        "استخدم مصطلحات زراعية ومرضية نباتية دقيقة. "
        "أبقِ مفاتيح JSON بالإنجليزية — فقط القيم النصية تكون بالعربية."
    ),
}


class AIProvider(ABC):
    """
    Abstract base for all AI vision providers.
    Every provider must implement analyze_image_structured so the
    rest of the application stays provider-agnostic.
    """

    @abstractmethod
    async def analyze_image_structured(
        self, image_bytes: bytes, language: str = "en"
    ) -> PlantAnalysisResult:
        """
        Analyse a plant image and return a validated PlantAnalysisResult.
        language: "en" (default) or "ar" — controls the language of all text fields.
        Raises AIServiceError on unrecoverable failures.
        """
        ...

    def _get_system_prompt(self, language: str = "en") -> str:
        language_instruction = _LANGUAGE_INSTRUCTIONS.get(
            language, _LANGUAGE_INSTRUCTIONS["en"]
        )
        return (
            "You are an expert plant pathologist AI (AgriVision). Analyse the uploaded image.\n\n"
            + language_instruction + "\n\n"
            "Strictly output VALID JSON matching EXACTLY this structure (no markdown fences):\n"
            "{\n"
            '    "is_plant": boolean,\n'
            '    "diagnosis": {\n'
            '        "name": "string",\n'
            '        "scientific_name": "string or null",\n'
            '        "confidence": float between 0 and 1,\n'
            '        "description": "string"\n'
            "    },\n"
            '    "severity": {\n'
            '        "level": "Healthy" | "Low" | "Medium" | "High" | "Critical",\n'
            '        "score": integer between 0 and 100,\n'
            '        "visual_indicators": ["string"]\n'
            "    },\n"
            '    "recommendation": "string"\n'
            "}\n\n"
            "Rules:\n"
            '1. If the image is NOT a plant, set "is_plant": false and fill other fields with nulls / sensible defaults.\n'
            "2. Severity score: 0 = perfect health, 100 = dead / unsalvageable.\n"
            "3. Be concise and actionable.\n"
            "4. Return ONLY the JSON object — no extra text, no markdown.\n"
            "5. severity.level must always be one of the exact English enum values listed above, regardless of output language.\n"
        )
# from abc import ABC, abstractmethod
# from app.models.schemas import PlantAnalysisResult


# class AIProvider(ABC):
#     """
#     Abstract base for all AI vision providers.
#     Every provider must implement analyze_image_structured so the
#     rest of the application stays provider-agnostic.
#     """

#     @abstractmethod
#     async def analyze_image_structured(self, image_bytes: bytes) -> PlantAnalysisResult:
#         """
#         Analyse a plant image and return a validated PlantAnalysisResult.
#         Raises AIServiceError on unrecoverable failures.
#         """
#         ...

#     # ------------------------------------------------------------------
#     # Shared prompt — identical expectations regardless of model backend
#     # ------------------------------------------------------------------
#     def _get_system_prompt(self) -> str:
#         return """
# You are an expert plant pathologist AI (AgriVision). Analyse the uploaded image.

# Strictly output VALID JSON matching EXACTLY this structure (no markdown fences):
# {
#     "is_plant": boolean,
#     "diagnosis": {
#         "name": "string",
#         "scientific_name": "string or null",
#         "confidence": float between 0 and 1,
#         "description": "string"
#     },
#     "severity": {
#         "level": "Healthy" | "Low" | "Medium" | "High" | "Critical",
#         "score": integer between 0 and 100,
#         "visual_indicators": ["string"]
#     },
#     "recommendation": "string"
# }

# Rules:
# 1. If the image is NOT a plant set "is_plant": false and fill other fields with nulls / sensible defaults.
# 2. Severity score: 0 = perfect health, 100 = dead / unsalvageable.
# 3. Be concise and actionable.
# 4. Return ONLY the JSON object — no extra text, no markdown.
# """