from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
# Removed unused 'Index' import

import uuid
from app.core.database import Base

class Scan(Base):
    __tablename__ = "scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Image Info
    image_url = Column(String, nullable=False)
    image_hash = Column(String, index=True, nullable=True) 
    
    # Diagnosis Summary
    diagnosis_name = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    severity_score = Column(Integer, nullable=False)
    
    # Full AI Result
    full_analysis = Column(JSONB, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to User
    user = relationship("User", backref="scans")