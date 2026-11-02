import uuid
import json
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, Text, DateTime
from sqlalchemy.orm import relationship
from ..database import Base

class ServiceProvider(Base):
    __tablename__ = "service_providers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    category = Column(String(30), nullable=False, index=True) # 'Repair', 'Resell', 'Donate', 'Refurbish', 'Recycle'
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False, index=True)
    contact_email = Column(String(150), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    website = Column(String(255), nullable=True)
    services_offered = Column(Text, default="[]") # JSON string list
    operating_hours = Column(String(150), nullable=True)
    is_verified = Column(Boolean, default=False)
    is_sample = Column(Boolean, default=True) # Explicit demo / sample flag
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    rating = Column(Float, default=4.5)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    recovery_requests = relationship("RecoveryRequest", back_populates="provider")

    def get_services(self):
        try:
            return json.loads(self.services_offered) if self.services_offered else []
        except Exception:
            return []
