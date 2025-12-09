from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, cast, Any
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID
from fastapi import HTTPException
from app.models.schemas import PlantAnalysisResult
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.scan import Scan

# Schema Definition
class ScanSummary(BaseModel):
    id: UUID
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
    
    return [ScanSummary.model_validate(scan) for scan in scans]

@router.get("/scans/{scan_id}", response_model=PlantAnalysisResult)
async def get_scan_detail(
    scan_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch the full analysis details for a specific scan.
    """
    query = select(Scan).where(
        Scan.id == scan_id, 
        Scan.user_id == current_user.id
    )
    
    result = await db.execute(query)
    scan = result.scalars().first()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Get the actual JSON data from the column
    # Cast to tell type checker this is a dict
    analysis_data = cast(dict[str, Any], scan.full_analysis)
    
    # Create a mutable copy and update the image_url
    data = dict(analysis_data) if analysis_data else {}
    data['image_url'] = scan.image_url
    
    return PlantAnalysisResult(**data)