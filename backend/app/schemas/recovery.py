from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class RecoveryRequestCreate(BaseModel):
    device_id: str
    assessment_id: str
    selected_route: str = Field(..., pattern="^(Repair|Reuse|Resell|Donate|Refurbish|Recycle)$")
    provider_id: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=2000)

class RecoveryStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(Request Created|Provider Selected|Device Submitted / Collected|Device Under Assessment|Recovery in Progress|Completed)$")
    notes: Optional[str] = Field(None, max_length=2000)

class StatusHistoryResponse(BaseModel):
    id: str
    recovery_request_id: str
    status: str
    notes: Optional[str] = None
    updated_by_user_id: Optional[str] = None
    updated_by_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RecoveryResponse(BaseModel):
    id: str
    user_id: str
    device_id: str
    device_name: Optional[str] = None
    device_category: Optional[str] = None
    assessment_id: str
    selected_route: str
    provider_id: Optional[str] = None
    provider_name: Optional[str] = None
    provider_category: Optional[str] = None
    current_status: str
    tracking_code: str
    notes: Optional[str] = None
    status_history: List[StatusHistoryResponse] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
