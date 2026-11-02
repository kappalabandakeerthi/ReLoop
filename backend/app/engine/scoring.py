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
from .eligibility import DeviceAssessmentInput, RouteEligibilityResult

@dataclass
class ScoringWeights:
    financial: float = 0.35
    useful_life: float = 0.30
    convenience: float = 0.15
    reuse: float = 0.20

    def validate(self) -> None:
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

def _estimate_replacement_benchmark(category: str) -> float:
    benchmarks = {
        "laptop": 800.0,
        "smartphone": 600.0,
        "tablet": 450.0,
        "monitor": 250.0,
        "desktop": 900.0,
        "printer": 200.0,
        "charger": 35.0,
        "other": 300.0,
    }
    return benchmarks.get(category.lower().strip(), 350.0)

def _calculate_financial_score(
    route: str,
    device: DeviceAssessmentInput,
    notes: List[str]
) -> float:
    """
    Computes normalized financial benefit score (0 - 100).
    Never defaults missing data to zero; uses contextual imputation.
    """
    cat = device.category.lower().strip()
    repl_cost = device.estimated_replacement_cost or _estimate_replacement_benchmark(cat)
    age = device.age_years if device.age_years is not None else 3.0
    cond = device.working_condition.lower().strip()

    if route == "Resell":
        if device.estimated_resale_value is not None and device.estimated_resale_value > 0:
            ratio = device.estimated_resale_value / repl_cost
            score = min(100.0, max(25.0, ratio * 130.0))
            notes.append(f"Resell financial score computed from user resale estimate (${device.estimated_resale_value:.2f})")
            return round(score, 1)
        else:
            # Impute based on age and condition without inventing fake figures
            base_ratio = max(0.15, 0.70 - (age * 0.08))
            if cond == "minor_issues":
                base_ratio *= 0.75
            score = min(95.0, max(30.0, base_ratio * 120.0))
            notes.append("Resell financial score derived from residual market depreciation model (no user estimate provided)")
            return round(score, 1)

    elif route == "Repair":
        rep_cost = device.estimated_repair_cost
        if rep_cost is not None and repl_cost > 0:
            savings = repl_cost - rep_cost
            savings_ratio = max(0.0, savings / repl_cost)
            # High savings ratio (e.g. 90% savings) gives high financial score (85 - 95)
            score = min(95.0, max(20.0, savings_ratio * 105.0))
            notes.append(f"Repair financial score calculated from net replacement savings (${savings:.2f})")
            return round(score, 1)
        else:
            # Default moderate-to-high financial viability if repairable faults present
            score = 75.0 if cond in ["minor_issues", "working"] else 50.0
            notes.append("Repair financial score estimated from typical component servicing savings")
            return round(score, 1)

    elif route == "Refurbish":
        # Trade-in / refurbisher payout is typically 65-80% of private resale
        if device.estimated_resale_value is not None:
            est_trade_in = device.estimated_resale_value * 0.75
            ratio = est_trade_in / repl_cost
            score = min(85.0, max(30.0, ratio * 110.0))
        else:
            base_ratio = max(0.12, 0.55 - (age * 0.07))
            score = min(85.0, max(28.0, base_ratio * 110.0))
        notes.append("Refurbish financial score based on certified trade-in valuation")
        return round(score, 1)

    elif route == "Donate":
        # Financial return is tax benefit or non-cash utility
        notes.append("Donate financial score reflects standard charitable item tax deduction utility")
        return 35.0

    elif route == "Recycle":
        # E-waste recycling typically has minimal or nominal material scrap payout
        notes.append("Recycle financial score reflects standard commodity materials scrap value")
        return 20.0

    return 50.0

def _calculate_useful_life_score(
    route: str,
    device: DeviceAssessmentInput,
    notes: List[str]
) -> float:
    """
    Computes useful life extension score (0 - 100).
    Measures duration the device remains active in service.
    """
    age = device.age_years if device.age_years is not None else 3.0
    exp_life = device.expected_remaining_life_years

    if route == "Repair":
        # Repairing directly adds 2 to 5 years of active operational life
        years_added = exp_life if exp_life is not None else max(2.0, 5.0 - (age * 0.4))
        score = min(98.0, max(50.0, years_added * 20.0 + 15.0))
        notes.append(f"Repair extends operational lifecycle by estimated {years_added:.1f} years")
        return round(score, 1)

    elif route == "Refurbish":
        # Professional overhaul extends useful life with tested parts
        years_added = exp_life if exp_life is not None else max(2.5, 6.0 - (age * 0.35))
        score = min(96.0, max(55.0, years_added * 18.0 + 20.0))
        notes.append(f"Refurbishment restores factory specifications, adding ~{years_added:.1f} years")
        return round(score, 1)

    elif route == "Resell":
        # Resale keeps existing working device active in secondary market
        years = max(1.5, 5.0 - (age * 0.5))
        score = min(90.0, max(45.0, years * 16.0 + 15.0))
        notes.append(f"Resale channels working device to secondary owner (~{years:.1f} yrs active use)")
        return round(score, 1)

    elif route == "Donate":
        # Donated devices provide 2 to 4 years of education / non-profit service
        years = max(1.5, 4.0 - (age * 0.4))
        score = min(85.0, max(40.0, years * 18.0 + 10.0))
        notes.append(f"Donation keeps device in service with students/charities (~{years:.1f} yrs)")
        return round(score, 1)

    elif route == "Recycle":
        # End of service life: device is disassembled for materials, zero operational life
        notes.append("Recycle concludes active device lifecycle; materials recovered for new manufacturing")
        return 18.0

    return 50.0

def _calculate_convenience_score(
    route: str,
    device: DeviceAssessmentInput,
    notes: List[str]
) -> float:
    """
    Computes convenience and accessibility score (0 - 100).
    Measures logistical simplicity, drop-off accessibility, and time commitment.
    """
    if route == "Recycle":
        # Very high convenience: authorized drop-off kiosks, municipal centers, retailers
        notes.append("Recycle offers highest convenience via standardized drop-off bins and collection points")
        return 92.0

    elif route == "Donate":
        # High convenience: local non-profit drop boxes, scheduled community pickups
        notes.append("Donate offers high convenience via local charity centers and scheduled pickups")
        return 82.0

    elif route == "Refurbish":
        # Good convenience: prepaid mail-in kits or certified drop-off partner counters
        notes.append("Refurbish offers moderate-to-high convenience via prepaid mail-in return kits")
        return 74.0

    elif route == "Repair":
        # Moderate convenience: requires bringing to local repair shop or waiting for diagnostics
        notes.append("Repair requires technician drop-off, diagnostic window, and pickup")
        return 68.0

    elif route == "Resell":
        # Lower convenience: requires photography, listing description, answering buyers, packaging/shipping
        notes.append("Resell requires listing creation, customer communication, and shipping/exchange logistics")
        return 50.0

    return 60.0

def _calculate_reuse_potential_score(
    route: str,
    device: DeviceAssessmentInput,
    notes: List[str]
) -> float:
    """
    Computes circular product utility score (0 - 100).
    Measures product preservation vs destructive material recovery.
    Note: Does NOT calculate environmental carbon emissions or eco metrics.
    """
    if route == "Donate":
        # 100% direct product reuse for public good
        notes.append("Donate delivers 100% direct product reuse to community beneficiaries")
        return 95.0

    elif route == "Resell":
        # High direct product reuse in secondary market
        notes.append("Resell achieves complete unit reuse with an active secondary user")
        return 90.0

    elif route == "Refurbish":
        # High product reuse after technical restoration
        notes.append("Refurbish preserves majority of chassis, display, and motherboard components")
        return 82.0

    elif route == "Repair":
        # Retains the device with original owner, replacing only worn subcomponents
        notes.append("Repair preserves device assembly by replacing only defective subcomponents")
        return 78.0

    elif route == "Recycle":
        # Shredding/melting components: low product reuse (only raw feedstock recovery)
        notes.append("Recycle recovers raw metals and plastics but terminates whole-device reuse")
        return 25.0

    return 50.0

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
        fin = _calculate_financial_score(route, device, notes)
        life = _calculate_useful_life_score(route, device, notes)
        conv = _calculate_convenience_score(route, device, notes)
        reuse = _calculate_reuse_potential_score(route, device, notes)

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
