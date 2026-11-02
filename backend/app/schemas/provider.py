from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class ProviderCreateRequest(BaseModel):
    name: str = Field(..., min_length=2)
    category: str = Field(..., pattern="^(Repair|Resell|Donate|Refurbish|Recycle)$")
    address: str = Field(..., min_length=5, max_length=500)
    city: str = Field(..., min_length=2, max_length=100)
    contact_email: Optional[str] = Field(None, max_length=150)
    contact_phone: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=255)
    services_offered: List[str] = Field(default_factory=list, max_length=30)
    operating_hours: Optional[str] = None
    is_verified: bool = False
    is_sample: bool = True
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[float] = Field(4.5, ge=0, le=5)

class ProviderUpdateRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    address: Optional[str] = Field(None, min_length=5, max_length=500)
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    contact_email: Optional[str] = Field(None, max_length=150)
    contact_phone: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=255)
    services_offered: Optional[List[str]] = Field(None, max_length=30)
    operating_hours: Optional[str] = None
    is_verified: Optional[bool] = None
    is_sample: Optional[bool] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[float] = Field(None, ge=0, le=5)

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

    model_config = ConfigDict(from_attributes=True)
