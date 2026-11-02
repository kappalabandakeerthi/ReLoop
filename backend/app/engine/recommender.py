"""
ReLoop Decision Engine - Master Recommender Pipeline
Integrates Stage A (Eligibility Rules) and Stage B (Multi-Criteria Weighted Scoring).
Generates transparent, auditable recovery recommendations and breakdowns.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from .eligibility import (
    DeviceAssessmentInput,
    RouteEligibilityResult,
    evaluate_recovery_eligibility,
    StageAOutput
)
from .scoring import (
    ScoringWeights,
    RouteScoreDetail,
    score_eligible_routes
)

@dataclass
class RecommendationOutput:
    recommended_route: str
    overall_score: float
    summary: str
    explanation: str
    all_scores: Dict[str, RouteScoreDetail]
    eligible_routes_ranked: List[str]
    ineligible_routes: List[str]
    is_fallback: bool
    fallback_message: Optional[str]
    device_summary: Dict[str, Any]
    weights_used: Dict[str, float]

def run_reloop_recommendation_pipeline(
    device: DeviceAssessmentInput,
    weights: Optional[ScoringWeights] = None
) -> RecommendationOutput:
    """
    Executes the two-stage decision pipeline:
    1. Evaluates feasibility of the 5 recovery routes.
    2. Ranks eligible options using weighted scoring.
    3. Handles insufficient information and edge cases gracefully.
    """
    if weights is None:
        weights = ScoringWeights()
    weights.validate()

    # Stage A: Eligibility
    stage_a: StageAOutput = evaluate_recovery_eligibility(device)

    # Stage B: Scoring
    scores = score_eligible_routes(device, stage_a.route_details, weights)

    # Filter and rank only eligible routes by final_score desc
    eligible_scored = [
        (route, score_detail)
        for route, score_detail in scores.items()
        if score_detail.is_eligible
    ]
    eligible_scored.sort(key=lambda x: x[1].final_score, reverse=True)
    ranked_route_names = [r for r, _ in eligible_scored]

    is_fallback = False
    fallback_msg = None

    if stage_a.insufficient_info:
        is_fallback = True
        fallback_msg = (
            "Insufficient device condition details were provided to reliably guarantee resale or repair. "
            "A professional diagnostic assessment is recommended before final commitment."
        )

    if not eligible_scored:
        # Ultimate fallback to Authorized Recycle if all other routes are disqualified
        top_route = "Recycle"
        top_score = scores["Recycle"].final_score if "Recycle" in scores else 50.0
        summary = "No refurbishment or resale options are feasible. Authorized E-Waste Recycling is the safest route."
        explanation = (
            "Due to severe damage, obsolete hardware, or prohibitive repair costs, "
            "all reuse options are ineligible. Certified e-waste recycling will safely handle materials."
        )
    else:
        top_route, top_detail = eligible_scored[0]
        top_score = top_detail.final_score

        # Generate narrative explanation
        if top_route == "Repair":
            summary = f"Repair is the optimal recovery route (Score: {top_score:.1f}/100) due to high economic savings and extended equipment life."
            explanation = (
                f"Your {device.brand} {device.model or device.category} has serviceable issues that can be restored economically. "
                f"Repairing yields substantial cost savings over replacement while extending operational utility by years. "
                f"Alternative routes like Resell or Donate scored lower because resolving the issue first delivers greater user value."
            )
        elif top_route == "Resell":
            summary = f"Resell is the optimal recovery route (Score: {top_score:.1f}/100), maximizing direct monetary recovery."
            explanation = (
                f"Your {device.brand} {device.model or device.category} is in good working order and commands strong secondary market demand. "
                f"Reselling returns direct cash value to you while transitioning a functional device to a new user. "
                f"Repair is not required as the unit operates normally."
            )
        elif top_route == "Donate":
            summary = f"Donate is the recommended recovery route (Score: {top_score:.1f}/100), providing immediate educational and community utility."
            explanation = (
                f"Your device powers on and meets community donation requirements. "
                f"Contributing this equipment directly benefits schools, non-profits, or low-income students in need of working technology."
            )
        elif top_route == "Refurbish":
            summary = f"Refurbish is the optimal recovery route (Score: {top_score:.1f}/100), leveraging certified facility restoration."
            explanation = (
                f"Your device has restorable commercial value best unlocked by a certified refurbisher with diagnostic benches and wholesale parts. "
                f"This route provides hassle-free return logistics and trade-in value."
            )
        else: # Recycle
            summary = f"Authorized Recycling is the recommended route (Score: {top_score:.1f}/100) for safe end-of-life recovery."
            explanation = (
                f"Due to the device's physical condition, age, or non-functional state, repair and resale are not economically viable. "
                f"Certified e-waste recycling ensures secure disposition and recovery of critical raw materials."
            )

    device_summary = {
        "category": device.category,
        "brand": device.brand,
        "model": device.model,
        "age_years": device.age_years,
        "working_condition": device.working_condition,
        "functional_status": device.functional_status,
        "overall_condition": device.overall_condition,
        "powers_on": device.powers_on,
        "physically_damaged": device.physically_damaged,
        "estimated_repair_cost": device.estimated_repair_cost,
        "estimated_resale_value": device.estimated_resale_value,
        "estimated_replacement_cost": device.estimated_replacement_cost,
        "expected_remaining_life_years": device.expected_remaining_life_years,
    }

    weights_dict = {
        "financial": weights.financial,
        "useful_life": weights.useful_life,
        "convenience": weights.convenience,
        "reuse": weights.reuse,
    }

    return RecommendationOutput(
        recommended_route=top_route,
        overall_score=top_score,
        summary=summary,
        explanation=explanation,
        all_scores=scores,
        eligible_routes_ranked=ranked_route_names,
        ineligible_routes=stage_a.ineligible_routes,
        is_fallback=is_fallback,
        fallback_message=fallback_msg,
        device_summary=device_summary,
        weights_used=weights_dict
    )
