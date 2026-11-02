from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class ProviderCreateRequest(BaseModel):
    name: str = Field(..., min_length=2)
    category: str = Field(..., pattern="^(Repair|Resell|Donate|Refurbish|Recycle)$")
    address: str
    city: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    services_offered: List[str] = Field(default_factory=list)
    operating_hours: Optional[str] = None
    is_verified: bool = False
    is_sample: bool = True
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[float] = 4.5

class ProviderUpdateRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    services_offered: Optional[List[str]] = None
    operating_hours: Optional[str] = None
    is_verified: Optional[bool] = None
    is_sample: Optional[bool] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[float] = None

class ProviderResponse(BaseModel):
    id: str
    name: str
    category: str
    address: str
    city: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    services_offered: List[str] = []
    operating_hours: Optional[str] = None
    is_verified: bool
    is_sample: bool
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[float] = 4.5
    created_at: datetime

    class Config:
        from_attributes = True
