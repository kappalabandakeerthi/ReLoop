import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

class RecoveryRequest(Base):
    __tablename__ = "recovery_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    selected_route = Column(String(30), nullable=False) # 'Repair', 'Resell', 'Donate', 'Refurbish', 'Recycle'
    provider_id = Column(String(36), ForeignKey("service_providers.id", ondelete="SET NULL"), nullable=True)
    current_status = Column(String(50), nullable=False, default="Request Created", index=True)
    tracking_code = Column(String(30), unique=True, nullable=False, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="recovery_requests")
    device = relationship("Device", back_populates="recovery_requests")
    assessment = relationship("Assessment", back_populates="recovery_requests")
    provider = relationship("ServiceProvider", back_populates="recovery_requests")
    status_history = relationship("RecoveryStatusHistory", back_populates="recovery_request", cascade="all, delete-orphan", order_by="RecoveryStatusHistory.created_at")

class RecoveryStatusHistory(Base):
    __tablename__ = "recovery_status_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recovery_request_id = Column(String(36), ForeignKey("recovery_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)
    updated_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    recovery_request = relationship("RecoveryRequest", back_populates="status_history")
    updated_by = relationship("User")
