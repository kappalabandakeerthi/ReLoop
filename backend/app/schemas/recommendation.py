from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class RecommendationScoreResponse(BaseModel):
    id: Optional[str] = None
    route: str
    is_eligible: bool
    final_score: float
    financial_score: float
    useful_life_score: float
    convenience_score: float
    reuse_score: float
    ineligible_reason: Optional[str] = None
    score_breakdown: Dict[str, Any] = {}

class RecommendationResponse(BaseModel):
    id: str
    assessment_id: str
    device_id: str
    recommended_route: str
    overall_score: float
    summary: str
    explanation: str
    weights_used: Dict[str, float]
    scores: List[RecommendationScoreResponse]
    eligible_routes_ranked: List[str]
    ineligible_routes: List[str]
    device_info: Optional[Dict[str, Any]] = None
    financial_summary: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
