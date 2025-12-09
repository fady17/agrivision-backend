from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID  # <--- NEW IMPORT

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.scan import Scan

# Schema Definition
class ScanSummary(BaseModel):
    id: UUID          # <--- CHANGED: Use UUID type here
    image_url: str
    diagnosis_name: str
    severity_score: int
    confidence: float
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

router = APIRouter()

@router.get("/scans", response_model=List[ScanSummary])
async def get_user_scans(
    skip: int = 0, 
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Scan)
        .where(Scan.user_id == current_user.id)
        .order_by(desc(Scan.created_at))
        .offset(skip)
        .limit(limit)
    )
    
    result = await db.execute(query)
    scans = result.scalars().all()
    
    return [
        ScanSummary.model_validate(scan)
        for scan in scans
    ]