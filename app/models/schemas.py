from pydantic import BaseModel
# from typing import Optional

class ImageUploadResult(BaseModel):
    image_id: str
    filename: str
    url: str
    content_type: str
    size: int

class ErrorResponse(BaseModel):
    detail: str