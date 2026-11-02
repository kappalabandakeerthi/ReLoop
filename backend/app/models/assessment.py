import uuid
import json
from datetime import datetime
from sqlalchemy import Column, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    overall_condition = Column(String(30), nullable=False) # excellent, good, fair, poor, unknown
    functional_status = Column(String(30), nullable=False) # fully_functional, partially_functional, non_functional, unknown
    specific_faults = Column(Text, default="[]") # stored as JSON string list
    estimated_repair_cost = Column(Float, nullable=True)
    estimated_resale_value = Column(Float, nullable=True)
    estimated_replacement_cost = Column(Float, nullable=True)
    expected_remaining_life_years = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    device = relationship("Device", back_populates="assessments")
    user = relationship("User", back_populates="assessments")
    recommendations = relationship("Recommendation", back_populates="assessment", cascade="all, delete-orphan")
    recovery_requests = relationship("RecoveryRequest", back_populates="assessment", cascade="all, delete-orphan")

    def get_faults_list(self):
        if not self.specific_faults:
            return []
        try:
            return json.loads(self.specific_faults)
        except Exception:
            return []
