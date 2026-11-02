import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.device import Device
from ..models.assessment import Assessment
from ..models.recommendation import Recommendation, RecommendationScore
from ..schemas.recommendation import RecommendationResponse, RecommendationScoreResponse
from ..utils.dependencies import get_current_user

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

def _format_recommendation_response(rec: Recommendation, db: Session) -> RecommendationResponse:
    assessment = db.query(Assessment).filter(Assessment.id == rec.assessment_id).first()
    device = db.query(Device).filter(Device.id == rec.device_id).first()

    scores = db.query(RecommendationScore).filter(RecommendationScore.recommendation_id == rec.id).all()
    score_responses = []
    eligible_ranked = []
    ineligible = []

    # Sort eligible by final_score desc
    sorted_scores = sorted(scores, key=lambda s: s.final_score, reverse=True)
    for s in sorted_scores:
        score_det = RecommendationScoreResponse(
            id=s.id,
            route=s.route,
            is_eligible=s.is_eligible,
            final_score=s.final_score,
            financial_score=s.financial_score,
            useful_life_score=s.useful_life_score,
            convenience_score=s.convenience_score,
            reuse_score=s.reuse_score,
            ineligible_reason=s.ineligible_reason,
            score_breakdown=s.get_breakdown()
        )
        score_responses.append(score_det)
        if s.is_eligible:
            eligible_ranked.append(s.route)
        else:
            ineligible.append(s.route)

    weights_dict = {}
    try:
        if rec.weights_used:
            weights_dict = json.loads(rec.weights_used)
    except Exception:
        pass

    device_info = {}
    if device:
        category_name = device.category.name if device.category else "Other"
        device_info = {
            "id": device.id,
            "name": device.name,
            "category": category_name,
            "brand": device.brand,
            "model": device.model,
            "age_years": device.approximate_age_years,
            "working_condition": device.working_condition,
            "powers_on": device.powers_on,
            "physically_damaged": device.physically_damaged,
            "contains_personal_data": device.contains_personal_data
        }

    financial_summary = {}
    if assessment:
        financial_summary = {
            "estimated_repair_cost": assessment.estimated_repair_cost,
            "estimated_resale_value": assessment.estimated_resale_value,
            "estimated_replacement_cost": assessment.estimated_replacement_cost,
            "expected_remaining_life_years": assessment.expected_remaining_life_years,
            "overall_condition": assessment.overall_condition,
            "functional_status": assessment.functional_status
        }

    return RecommendationResponse(
        id=rec.id,
        assessment_id=rec.assessment_id,
        device_id=rec.device_id,
        recommended_route=rec.recommended_route,
        overall_score=rec.overall_score,
        summary=rec.summary,
        explanation=rec.explanation,
        weights_used=weights_dict,
        scores=score_responses,
        eligible_routes_ranked=eligible_ranked,
        ineligible_routes=ineligible,
        device_info=device_info,
        financial_summary=financial_summary,
        created_at=rec.created_at
    )

@router.get("/{rec_id}", response_model=RecommendationResponse)
def get_recommendation_by_id(
    rec_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found.")
    
    # Check device ownership
    device = db.query(Device).filter(Device.id == rec.device_id).first()
    if device and device.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return _format_recommendation_response(rec, db)

@router.get("/device/{device_id}", response_model=RecommendationResponse)
def get_latest_recommendation_for_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
    if device.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    rec = db.query(Recommendation).filter(Recommendation.device_id == device_id).order_by(Recommendation.created_at.desc()).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No recommendation found for this device.")

    return _format_recommendation_response(rec, db)
