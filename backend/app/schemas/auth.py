from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

EMAIL_REGEX = r"^[\w\.\+-]+@[\w\.-]+\.\w+$"

class UserRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(..., pattern=EMAIL_REGEX)
    password: str = Field(..., min_length=12, max_length=72)
    full_name: str = Field(..., min_length=2)
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None

class UserLoginRequest(BaseModel):
    email: str = Field(..., pattern=EMAIL_REGEX)
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str
    role: str

class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    role: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
