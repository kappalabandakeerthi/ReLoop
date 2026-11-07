
"""
ReLoop Recovery Decision Engine
Stage B: Recovery Route Suitability Scoring

Stage A determines route eligibility.
Stage B calculates an independent suitability score
for each of the six recovery routes.

IMPORTANT:
These are heuristic suitability scores, NOT trained ML
probabilities. Missing information is excluded from scoring.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from app.engine.eligibility import (
    DeviceAssessmentInput,
    StageAOutput,
    evaluate_recovery_eligibility,
)


@dataclass
class RouteScore:
    route: str
    suitability_percent: Optional[float]
    eligible: bool
    confidence: str
    coverage_percent: float
    positive_factors: List[str]
    negative_factors: List[str]
    missing_information: List[str]
    eligibility_reason: str
    explanation: str


@dataclass
class StageBOutput:
    route_scores: Dict[str, RouteScore]
    scoring_note: str


# Expert-designed initial weights.
# These weights are not learned from historical data.

ROUTE_WEIGHTS = {
    "Repair": {
        "fault_severity": (25, "Specific fault details"),
        "repair_economics": (25, "Repair and replacement costs"),
        "condition": (20, "Working and functional condition"),
        "age": (15, "Device age"),
        "remaining_life": (15, "Expected remaining useful life"),
    },

    "Reuse": {
        "working_condition": (35, "Verified working condition"),
        "remaining_life": (25, "Expected remaining useful life"),
        "physical_condition": (15, "Physical condition"),
        "functional_status": (15, "Functional status"),
        "age": (10, "Device age"),
    },

    "Resell": {
        "resale_value": (30, "Estimated resale value"),
        "market_age": (25, "Device age and market viability"),
        "working_condition": (20, "Verified working condition"),
        "physical_condition": (15, "Physical condition"),
        "functionality": (10, "Functional status"),
    },

    "Refurbish": {
        "component_condition": (25, "Functional and physical condition"),
        "repair_economics": (25, "Repair and replacement costs"),
        "age": (20, "Device age"),
        "fault_severity": (15, "Specific fault details"),
        "remaining_life": (15, "Expected remaining useful life"),
    },

    "Donate": {
        "working_condition": (30, "Verified working condition"),
        "safety": (25, "Physical safety information"),
        "remaining_life": (20, "Expected remaining useful life"),
        "physical_condition": (10, "Overall physical condition"),
        "data_readiness": (15, "Personal-data removal confirmation"),
    },

    "Recycle": {
        "physical_state": (25, "Physical condition and damage"),
        "device_age": (15, "Device age"),
        "device_information": (15, "Device category and specifications"),
        "data_safety": (20, "Personal-data handling status"),
        "recovery_need": (25, "Device functional condition"),
    },
}


def _rating(value: float, reason: str) -> Tuple[float, str]:
    """Return a rating between 0 and 5 with an explanation."""
    return max(0, min(5, value)), reason


def _get_factor_ratings(
    device: DeviceAssessmentInput
) -> Dict[str, Optional[Tuple[float, str]]]:

    ratings = {}

    condition = device.working_condition.lower().strip()
    functional = device.functional_status.lower().strip()
    overall = device.overall_condition.lower().strip()

    # 1. Working condition
    condition_ratings = {
        "working": 5,
        "minor_issues": 3,
        "major_issues": 1,
        "not_working": 0,
    }

    ratings["working_condition"] = (
        _rating(
            condition_ratings[condition],
            f"Working condition is '{condition}'."
        )
        if condition in condition_ratings else None
    )

    ratings["condition"] = ratings["working_condition"]

    # 2. Functional status
    functional_ratings = {
        "fully_functional": 5,
        "partially_functional": 3,
        "non_functional": 0,
    }

    ratings["functional_status"] = (
        _rating(
            functional_ratings[functional],
            f"Functional status is '{functional}'."
        )
        if functional in functional_ratings else None
    )

    ratings["functionality"] = ratings["functional_status"]

    # 3. Physical condition
    physical_ratings = {
        "excellent": 5,
        "good": 4,
        "fair": 2,
        "poor": 0,
    }

    ratings["physical_condition"] = (
        _rating(
            physical_ratings[overall],
            f"Physical condition is '{overall}'."
        )
        if overall in physical_ratings else None
    )

    ratings["physical_state"] = ratings["physical_condition"]

    # 4. Safety
    if device.physically_damaged is True:
        ratings["safety"] = _rating(
            1,
            "Physical damage reported; safety inspection is required."
        )
    elif device.physically_damaged is False:
        ratings["safety"] = _rating(
            5,
            "No physical damage reported."
        )
    else:
        ratings["safety"] = None

    # 5. Device age
    if device.age_years is not None:
        age = device.age_years

        age_score = (
            5 if age <= 2 else
            4 if age <= 4 else
            3 if age <= 6 else
            2 if age <= 8 else
            1 if age <= 12 else 0
        )

        ratings["age"] = _rating(
            age_score,
            f"Device age is {age} years."
        )

        ratings["market_age"] = ratings["age"]
        ratings["device_age"] = ratings["age"]
    else:
        ratings["age"] = None
        ratings["market_age"] = None
        ratings["device_age"] = None

    # 6. Remaining useful life
    if device.expected_remaining_life_years is not None:
        life = device.expected_remaining_life_years

        life_score = (
            5 if life >= 5 else
            4 if life >= 3 else
            3 if life >= 2 else
            2 if life >= 1 else 0
        )

        ratings["remaining_life"] = _rating(
            life_score,
            f"Expected remaining life is {life} years."
        )
    else:
        ratings["remaining_life"] = None

    # 7. Repair economics
    if (
        device.estimated_repair_cost is not None
        and device.estimated_replacement_cost is not None
        and device.estimated_replacement_cost > 0
    ):
        ratio = (
            device.estimated_repair_cost
            / device.estimated_replacement_cost
        )

        economics_score = (
            5 if ratio <= 0.20 else
            4 if ratio <= 0.40 else
            3 if ratio <= 0.60 else
            2 if ratio <= 0.85 else 0
        )

        ratings["repair_economics"] = _rating(
            economics_score,
            f"Repair cost is {ratio * 100:.1f}% of replacement cost."
        )
    else:
        ratings["repair_economics"] = None

    # 8. Resale value
    if device.estimated_resale_value is not None:
        resale = device.estimated_resale_value

        resale_score = (
            5 if resale >= 500 else
            4 if resale >= 300 else
            3 if resale >= 150 else
            2 if resale > 0 else 0
        )

        ratings["resale_value"] = _rating(
            resale_score,
            f"Estimated resale value is ${resale:.2f}."
        )
    else:
        ratings["resale_value"] = None

    # 9. Fault severity
    faults = [
        fault.lower().strip()
        for fault in device.specific_faults
    ]

    if faults:
        severe_faults = {
            "severe_crush",
            "crushed",
            "shattered_panel_and_chassis",
            "fire_damage",
            "burnt",
            "run_over",
            "bent_chassis",
            "submerged_saltwater",
        }

        if any(fault in severe_faults for fault in faults):
            fault_score = 0
        elif len(faults) == 1:
            fault_score = 4
        elif len(faults) <= 3:
            fault_score = 3
        else:
            fault_score = 1

        ratings["fault_severity"] = _rating(
            fault_score,
            f"Reported faults: {', '.join(faults)}."
        )
    else:
        ratings["fault_severity"] = None

    # 10. Component condition
    if (
        ratings["functional_status"] is not None
        and ratings["physical_condition"] is not None
    ):
        component_score = (
            ratings["functional_status"][0]
            + ratings["physical_condition"][0]
        ) / 2

        ratings["component_condition"] = _rating(
            component_score,
            "Component condition estimated from functional and physical condition."
        )
    else:
        ratings["component_condition"] = None

    # 11. Personal data
    # Presence of personal data does not prove secure deletion.
    if device.contains_personal_data:
        ratings["data_readiness"] = _rating(
            1,
            "Personal data is present; secure wiping is required before donation."
        )

        ratings["data_safety"] = _rating(
            1,
            "Personal data is present; secure handling is required before recycling."
        )
    else:
        ratings["data_readiness"] = None
        ratings["data_safety"] = None

    # 12. Device information
    if device.category and device.category.lower() != "other":
        ratings["device_information"] = _rating(
            4,
            f"Device category identified as {device.category}."
        )
    else:
        ratings["device_information"] = None

    # 13. Recovery need
    if (
        ratings["physical_condition"] is not None
        and ratings["functional_status"] is not None
    ):
        recovery_score = (
            ratings["physical_condition"][0]
            + ratings["functional_status"][0]
        ) / 2

        ratings["recovery_need"] = _rating(
            recovery_score,
            "Estimated from physical and functional condition."
        )
    else:
        ratings["recovery_need"] = None

    return ratings


def _confidence_label(
    coverage: float,
    requires_assessment: bool
) -> str:

    if requires_assessment or coverage < 40:
        return "Low"

    if coverage < 75:
        return "Medium"

    return "High"


def _score_route(
    route: str,
    stage_a: StageAOutput,
    ratings: Dict[str, Optional[Tuple[float, str]]]
) -> RouteScore:

    eligibility = stage_a.route_details[route]

    # Stage A disqualification takes priority.
    if not eligibility.is_eligible:
        return RouteScore(
            route=route,
            suitability_percent=None,
            eligible=False,
            confidence="Not applicable",
            coverage_percent=0,
            positive_factors=[],
            negative_factors=[],
            missing_information=[],
            eligibility_reason=eligibility.reason,
            explanation="This route is ineligible according to Stage A."
        )

    weights = ROUTE_WEIGHTS[route]

    weighted_score = 0
    available_weight = 0

    positive = []
    negative = []
    missing = []

    for factor, (weight, missing_label) in weights.items():

        factor_result = ratings.get(factor)

        if factor_result is None:
            missing.append(missing_label)
            continue

        score, reason = factor_result

        weighted_score += score * weight
        available_weight += weight

        if score >= 4:
            positive.append(reason)
        elif score <= 2:
            negative.append(reason)

    total_weight = sum(
        weight for weight, _ in weights.values()
    )

    if available_weight == 0:
        suitability = None
        coverage = 0
    else:
        suitability = round(
            (weighted_score / available_weight) / 5 * 100,
            2
        )

        coverage = round(
            available_weight / total_weight * 100,
            2
        )

    confidence = _confidence_label(
        coverage,
        eligibility.requires_assessment
    )

    if suitability is None:
        explanation = (
            "Insufficient assessment data to calculate a "
            "meaningful suitability score."
        )
    else:
        explanation = (
            f"Estimated suitability: {suitability}%. "
            f"Assessment coverage: {coverage}%."
        )

    return RouteScore(
        route=route,
        suitability_percent=suitability,
        eligible=True,
        confidence=confidence,
        coverage_percent=coverage,
        positive_factors=positive,
        negative_factors=negative,
        missing_information=missing,
        eligibility_reason=eligibility.reason,
        explanation=explanation
    )


def evaluate_recovery_suitability(
    device: DeviceAssessmentInput,
    stage_a: Optional[StageAOutput] = None
) -> StageBOutput:
    """
    Evaluate all six recovery routes independently.

    Stage A runs automatically if its result is not supplied.
    """

    if stage_a is None:
        stage_a = evaluate_recovery_eligibility(device)

    ratings = _get_factor_ratings(device)

    route_scores = {}

    for route in [
        "Repair",
        "Reuse",
        "Resell",
        "Donate",
        "Refurbish",
        "Recycle"
    ]:

        route_scores[route] = _score_route(
            route,
            stage_a,
            ratings
        )

    return StageBOutput(
        route_scores=route_scores,
        scoring_note=(
            "Scores are independent heuristic suitability estimates, "
            "not calibrated probabilities. They do not need to add up "
            "to 100%. Missing criteria are excluded from scoring and "
            "reported through coverage and confidence."
        )
    )
