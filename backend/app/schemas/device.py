from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class CategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class DeviceCreateRequest(BaseModel):
    category_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=2)
    brand: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    purchase_year: Optional[int] = Field(None, ge=1970, le=2100)
    approximate_age_years: Optional[float] = Field(None, ge=0, le=100)
    working_condition: str = Field(..., pattern="^(working|minor_issues|major_issues|not_working|unknown)$")
    fault_description: Optional[str] = None
    powers_on: Optional[bool] = None
    physically_damaged: Optional[bool] = None
    contains_personal_data: bool = False

class DeviceUpdateRequest(BaseModel):
    category_id: Optional[int] = Field(None, gt=0)
    name: Optional[str] = Field(None, min_length=2)
    brand: Optional[str] = Field(None, min_length=1)
    model: Optional[str] = Field(None, min_length=1)
    purchase_year: Optional[int] = Field(None, ge=1970, le=2100)
    approximate_age_years: Optional[float] = Field(None, ge=0, le=100)
    working_condition: Optional[str] = Field(None, pattern="^(working|minor_issues|major_issues|not_working|unknown)$")
    fault_description: Optional[str] = None
    powers_on: Optional[bool] = None
    physically_damaged: Optional[bool] = None
    contains_personal_data: Optional[bool] = None

class DeviceResponse(BaseModel):
    id: str
    user_id: str
    category_id: int
    category_name: Optional[str] = None
    name: str
    brand: str
    model: str
    purchase_year: Optional[int] = None
    approximate_age_years: Optional[float] = None
    working_condition: str
    fault_description: Optional[str] = None
    powers_on: Optional[bool] = None
    physically_damaged: Optional[bool] = None
    contains_personal_data: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
