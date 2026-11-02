import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.device import Device
from ..models.assessment import Assessment
from ..models.recommendation import Recommendation, RecommendationScore
from ..schemas.assessment import AssessmentCreateRequest, AssessmentResponse
from ..schemas.recommendation import RecommendationResponse, RecommendationScoreResponse
from ..engine.eligibility import DeviceAssessmentInput
from ..engine.assessment_estimator import estimate_assessment_values
from ..engine.scoring import ScoringWeights
from ..engine.recommender import run_reloop_recommendation_pipeline
from ..utils.dependencies import get_current_user

router = APIRouter(prefix="/assessments", tags=["Assessments"])

@router.post("", response_model=RecommendationResponse, status_code=status.HTTP_201_CREATED)
def submit_device_assessment(
    assessment_data: AssessmentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify device exists and belongs to user (or admin)
    device = db.query(Device).filter(Device.id == assessment_data.device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
    if device.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    category_name = device.category.name if device.category else "Other"
    age_years = device.approximate_age_years
    if age_years is None and device.purchase_year is not None:
        age_years = max(0.0, float(datetime.now().year - device.purchase_year))

    estimates = estimate_assessment_values(
        category=category_name,
        brand=device.brand,
        model=device.model,
        age_years=age_years,
        overall_condition=assessment_data.overall_condition,
        functional_status=assessment_data.functional_status,
        specific_faults=assessment_data.specific_faults,
        physically_damaged=device.physically_damaged,
    )
    estimated_repair_cost = (
        assessment_data.estimated_repair_cost
        if assessment_data.estimated_repair_cost is not None
        else estimates.estimated_repair_cost
    )
    estimated_resale_value = (
        assessment_data.estimated_resale_value
        if assessment_data.estimated_resale_value is not None
        else estimates.estimated_resale_value
    )
    estimated_replacement_cost = (
        assessment_data.estimated_replacement_cost
        if assessment_data.estimated_replacement_cost is not None
        else estimates.estimated_replacement_cost
    )
    expected_remaining_life_years = (
        assessment_data.expected_remaining_life_years
        if assessment_data.expected_remaining_life_years is not None
        else estimates.expected_remaining_life_years
    )
    estimate_sources = {
        "estimated_repair_cost": "User-provided estimate" if assessment_data.estimated_repair_cost is not None else "ReLoop estimate",
        "estimated_resale_value": "User-provided estimate" if assessment_data.estimated_resale_value is not None else "ReLoop estimate",
        "estimated_replacement_cost": "User-provided estimate" if assessment_data.estimated_replacement_cost is not None else "ReLoop estimate",
        "expected_remaining_life_years": "User-provided estimate" if assessment_data.expected_remaining_life_years is not None else "ReLoop estimate",
    }

    # 1. Persist the assessment and computed estimates together.
    new_assessment = Assessment(
        device_id=device.id,
        user_id=device.user_id,
        overall_condition=assessment_data.overall_condition,
        functional_status=assessment_data.functional_status,
        specific_faults=json.dumps(assessment_data.specific_faults),
        estimated_repair_cost=estimated_repair_cost,
        estimated_resale_value=estimated_resale_value,
        estimated_replacement_cost=estimated_replacement_cost,
        expected_remaining_life_years=expected_remaining_life_years,
        notes=assessment_data.notes
    )
    db.add(new_assessment)
    db.flush()

    # 2. Build input for the Decision Engine
    engine_input = DeviceAssessmentInput(
        category=category_name,
        brand=device.brand,
        model=device.model,
        age_years=age_years,
        working_condition=device.working_condition,
        functional_status=assessment_data.functional_status,
        overall_condition=assessment_data.overall_condition,
        powers_on=device.powers_on,
        physically_damaged=device.physically_damaged,
        contains_personal_data=device.contains_personal_data,
        specific_faults=assessment_data.specific_faults,
        estimated_repair_cost=estimated_repair_cost,
        estimated_resale_value=estimated_resale_value,
        estimated_replacement_cost=estimated_replacement_cost,
        expected_remaining_life_years=expected_remaining_life_years
    )

    # Configurable weights support
    custom_weights = None
    if all(w is not None for w in [
        assessment_data.custom_weight_financial,
        assessment_data.custom_weight_useful_life,
        assessment_data.custom_weight_convenience,
        assessment_data.custom_weight_reuse
    ]):
        custom_weights = ScoringWeights(
            financial=assessment_data.custom_weight_financial,
            useful_life=assessment_data.custom_weight_useful_life,
            convenience=assessment_data.custom_weight_convenience,
            reuse=assessment_data.custom_weight_reuse
        )

    # 3. Execute Decision Pipeline
    recommendation_output = run_reloop_recommendation_pipeline(engine_input, custom_weights)

    # 4. Persist Recommendation & Scores
    new_rec = Recommendation(
        assessment_id=new_assessment.id,
        device_id=device.id,
        recommended_route=recommendation_output.recommended_route,
        overall_score=recommendation_output.overall_score,
        explanation=recommendation_output.explanation,
        summary=recommendation_output.summary,
        weights_used=json.dumps(recommendation_output.weights_used)
    )
    db.add(new_rec)
    db.flush()

    score_responses = []
    for route, score_det in recommendation_output.all_scores.items():
        rec_score = RecommendationScore(
            recommendation_id=new_rec.id,
            route=route,
            is_eligible=score_det.is_eligible,
            final_score=score_det.final_score,
            financial_score=score_det.financial_score,
            useful_life_score=score_det.useful_life_score,
            convenience_score=score_det.convenience_score,
            reuse_score=score_det.reuse_score,
            ineligible_reason=score_det.ineligible_reason,
            score_breakdown=json.dumps(score_det.breakdown)
        )
        db.add(rec_score)
        score_responses.append(
            RecommendationScoreResponse(
                route=route,
                is_eligible=score_det.is_eligible,
                final_score=score_det.final_score,
                financial_score=score_det.financial_score,
                useful_life_score=score_det.useful_life_score,
                convenience_score=score_det.convenience_score,
                reuse_score=score_det.reuse_score,
                ineligible_reason=score_det.ineligible_reason,
                score_breakdown=score_det.breakdown
            )
        )
    db.commit()
    db.refresh(new_rec)

    return RecommendationResponse(
        id=new_rec.id,
        assessment_id=new_assessment.id,
        device_id=device.id,
        recommended_route=new_rec.recommended_route,
        overall_score=new_rec.overall_score,
        summary=new_rec.summary,
        explanation=new_rec.explanation,
        weights_used=recommendation_output.weights_used,
        scores=score_responses,
        eligible_routes_ranked=recommendation_output.eligible_routes_ranked,
        ineligible_routes=recommendation_output.ineligible_routes,
        device_info={
            "name": device.name,
            "category": category_name,
            "brand": device.brand,
            "model": device.model,
            "age_years": device.approximate_age_years,
            "powers_on": device.powers_on,
            "contains_personal_data": device.contains_personal_data
        },
        financial_summary={
            "estimated_repair_cost": estimated_repair_cost,
            "estimated_resale_value": estimated_resale_value,
            "estimated_replacement_cost": estimated_replacement_cost,
            "expected_remaining_life_years": expected_remaining_life_years,
            "estimate_method": "category_age_condition_v1",
            "estimate_confidence": estimates.confidence,
            "estimate_sources": estimate_sources,
            "estimate_notes": estimates.notes,
            "estimate_ranges": estimates.ranges(),
            "matched_faults": estimates.matched_faults,
            "is_market_quote": False,
        },
        created_at=new_rec.created_at
    )

@router.get("/my", response_model=List[AssessmentResponse])
def get_my_assessments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    assessments = db.query(Assessment).filter(Assessment.user_id == current_user.id).order_by(Assessment.created_at.desc()).all()
    results = []
    for a in assessments:
        results.append(
            AssessmentResponse(
                id=a.id,
                device_id=a.device_id,
                user_id=a.user_id,
                overall_condition=a.overall_condition,
                functional_status=a.functional_status,
                specific_faults=a.get_faults_list(),
                estimated_repair_cost=a.estimated_repair_cost,
                estimated_resale_value=a.estimated_resale_value,
                estimated_replacement_cost=a.estimated_replacement_cost,
                expected_remaining_life_years=a.expected_remaining_life_years,
                notes=a.notes,
                created_at=a.created_at
            )
        )
    return results

@router.get("/{assessment_id}", response_model=AssessmentResponse)
def get_assessment_by_id(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    a = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")
    if a.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return AssessmentResponse(
        id=a.id,
        device_id=a.device_id,
        user_id=a.user_id,
        overall_condition=a.overall_condition,
        functional_status=a.functional_status,
        specific_faults=a.get_faults_list(),
        estimated_repair_cost=a.estimated_repair_cost,
        estimated_resale_value=a.estimated_resale_value,
        estimated_replacement_cost=a.estimated_replacement_cost,
        expected_remaining_life_years=a.expected_remaining_life_years,
        notes=a.notes,
        created_at=a.created_at
    )
