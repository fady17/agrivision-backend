from pydantic import BaseModel
from typing import List, Optional
from app.models.schemas import PlantAnalysisResult


class ChatMessage(BaseModel):
    role: str
    content: str
    image_b64: Optional[str] = None
    image_mime: Optional[str] = None   # e.g. 'image/jpeg', 'image/png'


class ChatRequest(BaseModel):
    # None when the user starts a free-form chat not linked to any scan
    analysis_context: Optional[PlantAnalysisResult] = None
    messages: List[ChatMessage]
    language: str = "en"