from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator

class AssessmentCreateRequest(BaseModel):
    device_id: str
    overall_condition: str = Field(..., pattern="^(excellent|good|fair|poor|unknown)$")
    functional_status: str = Field(..., pattern="^(fully_functional|partially_functional|non_functional|unknown)$")
    specific_faults: List[str] = Field(default_factory=list, max_length=40)
    estimated_repair_cost: Optional[float] = Field(None, ge=0, le=100000000)
    estimated_resale_value: Optional[float] = Field(None, ge=0, le=100000000)
    estimated_replacement_cost: Optional[float] = Field(None, gt=0, le=100000000)
    expected_remaining_life_years: Optional[float] = Field(None, ge=0, le=100)
    notes: Optional[str] = Field(None, max_length=2000)
    # Optional custom weighting overrides (if provided, must sum to 1.0)
    custom_weight_financial: Optional[float] = Field(None, ge=0, le=1)
    custom_weight_useful_life: Optional[float] = Field(None, ge=0, le=1)
    custom_weight_convenience: Optional[float] = Field(None, ge=0, le=1)
    custom_weight_reuse: Optional[float] = Field(None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_custom_weights(self):
        weights = [
            self.custom_weight_financial,
            self.custom_weight_useful_life,
            self.custom_weight_convenience,
            self.custom_weight_reuse,
        ]
        supplied = [weight is not None for weight in weights]
        if any(supplied) and not all(supplied):
            raise ValueError("Provide all four custom weights or leave them all unset.")
        if all(supplied) and abs(sum(weights) - 1.0) > 0.001:
            raise ValueError("Custom weights must sum to 1.0.")
        return self

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

    model_config = ConfigDict(from_attributes=True)
