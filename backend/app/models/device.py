import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

class DeviceCategory(Base):
    __tablename__ = "device_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    devices = relationship("Device", back_populates="category")

class Device(Base):
    __tablename__ = "devices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("device_categories.id"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    brand = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    purchase_year = Column(Integer, nullable=True)
    approximate_age_years = Column(Float, nullable=True)
    working_condition = Column(String(30), nullable=False, default="unknown") # working, minor_issues, major_issues, not_working, unknown
    fault_description = Column(Text, nullable=True)
    powers_on = Column(Boolean, nullable=True)
    physically_damaged = Column(Boolean, nullable=True)
    contains_personal_data = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="devices")
    category = relationship("DeviceCategory", back_populates="devices")
    assessments = relationship("Assessment", back_populates="device", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="device", cascade="all, delete-orphan")
    recovery_requests = relationship("RecoveryRequest", back_populates="device", cascade="all, delete-orphan")
