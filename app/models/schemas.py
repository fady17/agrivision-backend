from pydantic import BaseModel, Field
from typing import List, Optional

class ImageUploadResult(BaseModel):
    image_id: str
    filename: str
    url: str
    content_type: str
    size: int

class ErrorResponse(BaseModel):
    detail: str

class Diagnosis(BaseModel):
    name: str = Field(description="Name of the disease, pest, or 'Healthy'")
    scientific_name: Optional[str] = Field(description="Scientific name if applicable")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    description: str = Field(description="Brief, non-technical description of the finding")

class Severity(BaseModel):
    level: str = Field(description="Health Tier: Healthy, Low, Medium, High, Critical")
    score: int = Field(description="0-100 score (0=Healthy, 100=Dead)")
    visual_indicators: List[str] = Field(description="List of specific visual signs used for this score")

class PlantAnalysisResult(BaseModel):
    is_plant: bool = Field(description="True if image contains a plant")
    image_url: Optional[str] = Field(None, description="URL of the uploaded image")
    diagnosis: Diagnosis
    severity: Severity
    recommendation: str = Field(description="Actionable advice for the farmer")

class APIResponse(BaseModel):
    status: str
    data: Optional[PlantAnalysisResult] = None
    error: Optional[str] = None