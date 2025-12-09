from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.scan import Scan

# Schema Definition
class ScanSummary(BaseModel):
    id: str
    image_url: str
    diagnosis_name: str
    severity_score: int
    confidence: float
    created_at: datetime
    
    # This config tells Pydantic to read data from ORM objects
    model_config = ConfigDict(from_attributes=True)

router = APIRouter()

@router.get("/scans", response_model=List[ScanSummary])
async def get_user_scans(
    skip: int = 0, 
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch paginated history of scans for the current user.
    """
    # Query: Select scans for this user, newest first
    query = (
        select(Scan)
        .where(Scan.user_id == current_user.id)
        .order_by(desc(Scan.created_at))
        .offset(skip)
        .limit(limit)
    )
    
    result = await db.execute(query)
    scans = result.scalars().all()
    
    # Use Pydantic to validate/convert SQLAlchemy models to JSON
    return [
        ScanSummary.model_validate(scan)
        for scan in scans
    ]