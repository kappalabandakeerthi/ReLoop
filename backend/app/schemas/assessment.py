from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class AssessmentCreateRequest(BaseModel):
    device_id: str
    overall_condition: str = Field(..., pattern="^(excellent|good|fair|poor|unknown)$")
    functional_status: str = Field(..., pattern="^(fully_functional|partially_functional|non_functional|unknown)$")
    specific_faults: List[str] = Field(default_factory=list)
    estimated_repair_cost: Optional[float] = None
    estimated_resale_value: Optional[float] = None
    estimated_replacement_cost: Optional[float] = None
    expected_remaining_life_years: Optional[float] = None
    notes: Optional[str] = None
    # Optional custom weighting overrides (if provided, must sum to 1.0)
    custom_weight_financial: Optional[float] = None
    custom_weight_useful_life: Optional[float] = None
    custom_weight_convenience: Optional[float] = None
    custom_weight_reuse: Optional[float] = None

class AssessmentResponse(BaseModel):
    id: str
    device_id: str
    user_id: str
    overall_condition: str
    functional_status: str
    specific_faults: List[str]
    estimated_repair_cost: Optional[float] = None
    estimated_resale_value: Optional[float] = None
    estimated_replacement_cost: Optional[float] = None
    expected_remaining_life_years: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
