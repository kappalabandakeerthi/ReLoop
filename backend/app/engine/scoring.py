"""
ReLoop Recovery Decision Engine - Stage B: Option Ranking
Ranks only eligible recovery options using configurable weighted scoring.

Parameters & Initial Default Weights:
- Financial Benefit: 35% (0.35)
- Remaining Useful Life: 30% (0.30)
- Convenience and Distance: 15% (0.15)
- Reuse Potential: 20% (0.20)
Total: 100% (1.00)

Final Score = Sum of (Parameter Weight * Normalized Parameter Score [0 - 100])
Note: Does NOT utilize any environmental metrics or carbon calculations.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from math import isfinite
from .eligibility import DeviceAssessmentInput, RouteEligibilityResult
from .assessment_estimator import (
    CONDITION_MULTIPLIERS,
    EXPECTED_SERVICE_LIFE,
    estimate_assessment_values,
)
from ..config import settings

@dataclass
class ScoringWeights:
    financial: float = settings.WEIGHT_FINANCIAL
    useful_life: float = settings.WEIGHT_USEFUL_LIFE
    convenience: float = settings.WEIGHT_CONVENIENCE
    reuse: float = settings.WEIGHT_REUSE

    def validate(self) -> None:
        values = (self.financial, self.useful_life, self.convenience, self.reuse)
        if any(not isfinite(value) or value < 0 or value > 1 for value in values):
            raise ValueError("Each scoring weight must be between 0 and 1.")
        total = self.financial + self.useful_life + self.convenience + self.reuse
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Weights must sum to 1.0 (current sum: {total:.4f})")

@dataclass
class RouteScoreDetail:
    route: str
    is_eligible: bool
    final_score: float
    financial_score: float
    useful_life_score: float
    convenience_score: float
    reuse_score: float
    explanation: str
    ineligible_reason: Optional[str] = None
    breakdown: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class _DeviceScoreContext:
    category: str
    replacement_cost: float
    repair_cost: float
    resale_value: float
    remaining_life_years: float
    service_life_years: float
    age_years: float
    condition_factor: float
    functionality_factor: float
    fault_count: int
    matched_faults: List[str]
    contains_personal_data: bool
    physically_damaged: bool
    powers_on: Optional[bool]


def _score_context(device: DeviceAssessmentInput) -> _DeviceScoreContext:
    estimates = estimate_assessment_values(
        category=device.category,
        brand=device.brand,
        model=device.model,
        age_years=device.age_years,
        overall_condition=device.overall_condition,
        functional_status=device.functional_status,
        specific_faults=device.specific_faults,
        physically_damaged=device.physically_damaged,
    )
    category = device.category.lower().strip()
    service_life = EXPECTED_SERVICE_LIFE.get(category, EXPECTED_SERVICE_LIFE["other"])
    condition = device.overall_condition.lower().strip()
    condition_factor = min(1.0, CONDITION_MULTIPLIERS.get(condition, CONDITION_MULTIPLIERS["unknown"]))
    functional = device.functional_status.lower().strip()
    if functional == "fully_functional":
        functionality_factor = 1.0
    elif functional == "partially_functional":
        functionality_factor = 0.65 if device.powers_on is True else 0.4
    elif functional == "non_functional":
        functionality_factor = 0.0
    else:
        functionality_factor = 0.35 if device.powers_on is True else 0.2

    return _DeviceScoreContext(
        category=category,
        replacement_cost=device.estimated_replacement_cost if device.estimated_replacement_cost is not None else estimates.estimated_replacement_cost,
        repair_cost=device.estimated_repair_cost if device.estimated_repair_cost is not None else estimates.estimated_repair_cost,
        resale_value=device.estimated_resale_value if device.estimated_resale_value is not None else estimates.estimated_resale_value,
        remaining_life_years=device.expected_remaining_life_years if device.expected_remaining_life_years is not None else estimates.expected_remaining_life_years,
        service_life_years=service_life,
        age_years=max(0.0, device.age_years if device.age_years is not None else service_life * 0.6),
        condition_factor=condition_factor,
        functionality_factor=functionality_factor,
        fault_count=len(estimates.matched_faults),
        matched_faults=estimates.matched_faults,
        contains_personal_data=device.contains_personal_data,
        physically_damaged=bool(device.physically_damaged),
        powers_on=device.powers_on,
    )


def _bounded_score(value: float) -> float:
    return round(min(100.0, max(0.0, value)), 1)

def _calculate_financial_score(
    route: str,
    device: DeviceAssessmentInput,
    notes: List[str],
    context: Optional[_DeviceScoreContext] = None,
) -> float:
    """Score monetary value relative to this device's model-adjusted replacement cost."""
    context = context or _score_context(device)
    replacement = max(context.replacement_cost, 1.0)
    repair = max(0.0, context.repair_cost)
    resale = max(0.0, context.resale_value)
    repair_ratio = repair / replacement
    resale_ratio = resale / replacement

    if route == "Repair":
        savings = replacement - repair
        notes.append(f"{route} avoids ${max(0.0, savings):.2f} of replacement cost after estimated service expense.")
        return _bounded_score(savings / replacement * 100.0)
    if route in {"Reuse", "Resell", "Donate"}:
        value_score = resale_ratio * (context.condition_factor if route == "Reuse" else 1.0)
        notes.append(
            f"{route} retained-value score compares ${resale:.2f} estimated device value "
            f"with ${replacement:.2f} model-specific replacement cost."
        )
        if route == "Donate":
            notes.append("Donation value is non-cash value transferred to a recipient.")
        return _bounded_score(value_score * 100.0)
    if route == "Refurbish":
        net_value = resale - repair
        notes.append(f"Refurbishment net value uses ${resale:.2f} resale value less ${repair:.2f} estimated repair cost.")
        return _bounded_score(net_value / replacement * 100.0)
    if route == "Recycle":
        recycling_fit = repair_ratio * max(0.0, 1.0 - resale_ratio)
        notes.append(
            f"Recycling financial fit reflects ${repair:.2f} estimated repair cost versus "
            f"${replacement:.2f} replacement cost and ${resale:.2f} resale value; recycler payout is unknown."
        )
        return _bounded_score(recycling_fit * 100.0)
    return 0.0

def _calculate_useful_life_score(
    route: str,
    device: DeviceAssessmentInput,
    notes: List[str],
    context: Optional[_DeviceScoreContext] = None,
) -> float:
    """Normalize estimated useful service against the category's expected service life."""
    context = context or _score_context(device)
    if route == "Recycle":
        notes.append("Recycling does not extend the device's active service life.")
        return 0.0

    remaining_life = context.remaining_life_years
    if route in {"Reuse", "Resell", "Donate"}:
        remaining_life *= context.functionality_factor
    score = _bounded_score(remaining_life / max(context.service_life_years, 1.0) * 100.0)
    notes.append(
        f"{route} useful-life score uses {remaining_life:.1f} estimated active years "
        f"against {context.service_life_years:.1f} expected years for this category."
    )
    return score

def _calculate_convenience_score(
    route: str,
    device: DeviceAssessmentInput,
    notes: List[str],
    context: Optional[_DeviceScoreContext] = None,
) -> float:
    """Convert estimated handling effort into convenience; no provider-distance data is available."""
    context = context or _score_context(device)
    device_handling = {
        "smartphone": 5, "tablet": 10, "laptop": 15, "charger": 3,
        "monitor": 30, "desktop": 35, "printer": 30, "other": 20,
    }.get(context.category, 20)
    fault_handling = context.fault_count * (8 if route in {"Repair", "Refurbish"} else 4)
    handoff = route != "Reuse"
    effort_minutes = 0 if not handoff else device_handling + fault_handling
    if route in {"Repair", "Refurbish"}:
        effort_minutes += 12 + min(35, max(0.0, context.repair_cost / max(context.replacement_cost, 1.0)) * 35)
    elif route == "Resell":
        effort_minutes += 28 + (1.0 - context.functionality_factor) * 24
    elif route == "Donate":
        effort_minutes += 12 + (1.0 - context.functionality_factor) * 18
    elif route == "Recycle":
        effort_minutes += 8 + context.fault_count * 3
    if handoff and context.contains_personal_data:
        effort_minutes += 18
    if handoff and context.physically_damaged:
        effort_minutes += 12
    if handoff and context.powers_on is False:
        effort_minutes += 8
    effort_minutes += max(0.0, context.age_years - context.service_life_years) * 2

    score = _bounded_score(100.0 / (1.0 + effort_minutes / 60.0))
    notes.append(
        f"Convenience estimates {effort_minutes:.0f} handling minutes for {route}, "
        "including device size, hand-off, fault checks, privacy, and damage factors."
    )
    notes.append("Provider distance and local travel time are not included.")
    return score

def _calculate_reuse_potential_score(
    route: str,
    device: DeviceAssessmentInput,
    notes: List[str],
    context: Optional[_DeviceScoreContext] = None,
) -> float:
    """Score the chance of keeping this particular device in useful service."""
    context = context or _score_context(device)
    if route == "Recycle":
        notes.append("Recycling does not keep the whole device in service; no environmental score is included.")
        return 0.0

    life_factor = min(1.0, context.remaining_life_years / max(context.service_life_years, 1.0))
    if route in {"Reuse", "Resell", "Donate"}:
        score = 100.0 * life_factor * context.condition_factor * context.functionality_factor
        notes.append(
            f"{route} reuse potential uses {context.matched_faults or ['no reported faults']}, "
            f"condition, functionality, and {context.remaining_life_years:.1f} remaining years."
        )
        return _bounded_score(score)

    if route == "Repair":
        retained_value_factor = max(0.0, (context.replacement_cost - context.repair_cost) / max(context.replacement_cost, 1.0))
        notes.append("Repair reuse potential combines remaining service life with value retained after repair cost.")
        return _bounded_score(100.0 * life_factor * retained_value_factor)

    if route == "Refurbish":
        recovery_value_factor = min(1.0, context.resale_value / max(context.replacement_cost, 1.0))
        notes.append("Refurbish reuse potential uses the device's estimated post-service resale value and remaining life.")
        return _bounded_score(100.0 * life_factor * recovery_value_factor)

    return 0.0

def score_eligible_routes(
    device: DeviceAssessmentInput,
    eligibility_results: Dict[str, RouteEligibilityResult],
    weights: Optional[ScoringWeights] = None
) -> Dict[str, RouteScoreDetail]:
    """
    Calculates weighted multi-criteria scores for all recovery routes.
    Ineligible routes are scored with is_eligible=False and preserved for transparency.
    """
    if weights is None:
        weights = ScoringWeights()
    weights.validate()
    context = _score_context(device)

    scored_routes: Dict[str, RouteScoreDetail] = {}

    for route, elig in eligibility_results.items():
        if not elig.is_eligible:
            scored_routes[route] = RouteScoreDetail(
                route=route,
                is_eligible=False,
                final_score=0.0,
                financial_score=0.0,
                useful_life_score=0.0,
                convenience_score=0.0,
                reuse_score=0.0,
                explanation=f"Option not recommended: {elig.reason}",
                ineligible_reason=elig.reason,
                breakdown={
                    "is_eligible": False,
                    "reason": elig.reason
                }
            )
            continue

        notes: List[str] = []
        fin = _calculate_financial_score(route, device, notes, context)
        life = _calculate_useful_life_score(route, device, notes, context)
        conv = _calculate_convenience_score(route, device, notes, context)
        reuse = _calculate_reuse_potential_score(route, device, notes, context)

        # Weighted calculation
        final = (
            (weights.financial * fin) +
            (weights.useful_life * life) +
            (weights.convenience * conv) +
            (weights.reuse * reuse)
        )
        final = round(final, 2)

        summary_explanation = (
            f"{route} scored {final:.1f}/100 based on "
            f"Financial Benefit ({fin:.1f} × {int(weights.financial*100)}%), "
            f"Useful Life ({life:.1f} × {int(weights.useful_life*100)}%), "
            f"Convenience ({conv:.1f} × {int(weights.convenience*100)}%), and "
            f"Reuse Potential ({reuse:.1f} × {int(weights.reuse*100)}%)."
        )

        scored_routes[route] = RouteScoreDetail(
            route=route,
            is_eligible=True,
            final_score=final,
            financial_score=fin,
            useful_life_score=life,
            convenience_score=conv,
            reuse_score=reuse,
            explanation=summary_explanation,
            ineligible_reason=None,
            breakdown={
                "financial_score": fin,
                "useful_life_score": life,
                "convenience_score": conv,
                "reuse_score": reuse,
                "weights": {
                    "financial": weights.financial,
                    "useful_life": weights.useful_life,
                    "convenience": weights.convenience,
                    "reuse": weights.reuse,
                },
                "evaluation_notes": notes
            }
        )

    return scored_routes
