from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, cast, Any, Dict
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID
from fastapi import HTTPException
from app.models.schemas import PlantAnalysisResult
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.scan import Scan
from app.services.storage_service import storage_service 

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
    
    # Refresh URLs before returning
    results = []
    for scan in scans:
        # Convert ORM object to Pydantic model
        summary = ScanSummary.model_validate(scan)
        # OVERWRITE the expired URL with a fresh one
        summary.image_url = storage_service.get_fresh_url(str(scan.image_url))
        results.append(summary)
        
    return results

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
    
    # TYPE FIX: Cast the JSONB column to a standard Python Dictionary
    # This tells Pylance: "Trust me, this is a Dict with string keys"
    raw_analysis = cast(Dict[str, Any], scan.full_analysis)
    
    # Create a copy so we can modify it
    data = raw_analysis.copy()
    
    # Refresh the URL using the storage service logic
    # We cast scan.image_url to str to be safe
    data['image_url'] = storage_service.get_fresh_url(str(scan.image_url))
    
    # Now Pylance knows 'data' is Dict[str, Any], so unpacking works
    return PlantAnalysisResult(**data)