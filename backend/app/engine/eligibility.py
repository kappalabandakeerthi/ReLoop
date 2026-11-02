"""
ReLoop Recovery Decision Engine - Stage A: Recovery Eligibility
Determines which recovery routes are feasible based on device specifications,
working condition, physical state, age, and specific faults.

Separation of Concerns:
This module evaluates ONLY route eligibility and records explicit disqualification
reasons. Option ranking and weighted scoring are handled in stage B (scoring.py).
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

ROUTES = ["Repair", "Reuse", "Resell", "Donate", "Refurbish", "Recycle"]

@dataclass
class DeviceAssessmentInput:
    category: str # 'Laptop', 'Smartphone', 'Tablet', 'Monitor', 'Desktop', 'Printer', 'Charger', 'Other'
    brand: str = ""
    model: str = ""
    age_years: Optional[float] = None
    working_condition: str = "unknown" # 'working', 'minor_issues', 'major_issues', 'not_working', 'unknown'
    functional_status: str = "unknown" # 'fully_functional', 'partially_functional', 'non_functional', 'unknown'
    overall_condition: str = "unknown" # 'excellent', 'good', 'fair', 'poor', 'unknown'
    powers_on: Optional[bool] = None
    physically_damaged: Optional[bool] = None
    contains_personal_data: bool = False
    specific_faults: List[str] = field(default_factory=list)
    estimated_repair_cost: Optional[float] = None
    estimated_resale_value: Optional[float] = None
    estimated_replacement_cost: Optional[float] = None
    expected_remaining_life_years: Optional[float] = None

@dataclass
class RouteEligibilityResult:
    route: str
    is_eligible: bool
    reason: str
    requires_assessment: bool = False

@dataclass
class StageAOutput:
    eligible_routes: List[str]
    ineligible_routes: List[str]
    route_details: Dict[str, RouteEligibilityResult]
    insufficient_info: bool = False
    guidance_note: str = ""

def evaluate_recovery_eligibility(device: DeviceAssessmentInput) -> StageAOutput:
    """
    Evaluates eligibility for each of the 5 recovery routes.
    Implements rule-based feasibility checks based on device health,
    fault severity, economics, age, and safety constraints.
    """
    faults_lower = [f.lower().strip() for f in device.specific_faults]
    cat_lower = device.category.lower().strip()
    cond_lower = device.working_condition.lower().strip()
    func_lower = device.functional_status.lower().strip()
    overall_lower = device.overall_condition.lower().strip()
    
    # Severe unrepairable destruction indicators
    severe_crush_indicators = {
        "severe_crush", "crushed", "shattered_panel_and_chassis", "fire_damage",
        "burnt", "run_over", "bent_chassis", "submerged_saltwater"
    }
    has_catastrophic_damage = any(ind in f for f in faults_lower for ind in severe_crush_indicators)
    
    # Check for insufficient information
    is_unknown_condition = (
        (cond_lower == "unknown" or func_lower == "unknown")
        and device.powers_on is None
        and len(faults_lower) == 0
    )

    results: Dict[str, RouteEligibilityResult] = {}

    # -------------------------------------------------------------
    # 1. REPAIR ELIGIBILITY
    # -------------------------------------------------------------
    if cat_lower == "charger":
        results["Repair"] = RouteEligibilityResult(
            route="Repair",
            is_eligible=False,
            reason="Generic chargers and cables are sealed consumable units; repair is hazardous and economically unviable."
        )
    elif has_catastrophic_damage:
        results["Repair"] = RouteEligibilityResult(
            route="Repair",
            is_eligible=False,
            reason="Device has sustained catastrophic physical destruction beyond economical or structural repair limits."
        )
    elif (device.estimated_repair_cost is not None 
          and device.estimated_replacement_cost is not None 
          and device.estimated_replacement_cost > 0 
          and device.estimated_repair_cost > 0.85 * device.estimated_replacement_cost):
        results["Repair"] = RouteEligibilityResult(
            route="Repair",
            is_eligible=False,
            reason=f"Estimated repair cost (${device.estimated_repair_cost:.2f}) exceeds 85% of replacement cost (${device.estimated_replacement_cost:.2f}), making repair economically non-viable."
        )
    elif (cond_lower == "working" and func_lower == "fully_functional" and len(faults_lower) == 0):
        # Device is already completely functional; repair is not needed
        results["Repair"] = RouteEligibilityResult(
            route="Repair",
            is_eligible=False,
            reason="Device is already fully functional with no reported faults; repair is not required."
        )
    elif is_unknown_condition:
        results["Repair"] = RouteEligibilityResult(
            route="Repair",
            is_eligible=True,
            reason="Device condition is unverified; diagnostic repair assessment recommended to identify internal faults.",
            requires_assessment=True
        )
    else:
        results["Repair"] = RouteEligibilityResult(
            route="Repair",
            is_eligible=True,
            reason="Identified faults or component wear appear serviceable by a qualified technician."
        )


    # 2. REUSE ELIGIBILITY (continue using the device as-is)
    if has_catastrophic_damage or device.powers_on is False or func_lower == "non_functional" or cond_lower == "not_working":
        results["Reuse"] = RouteEligibilityResult(
            route="Reuse",
            is_eligible=False,
            reason="The device is not currently safe or functional enough for continued use."
        )
    elif is_unknown_condition or (device.powers_on is None and func_lower != "fully_functional"):
        results["Reuse"] = RouteEligibilityResult(
            route="Reuse",
            is_eligible=False,
            reason="Confirm that the device powers on and functions reliably before continuing to use it.",
            requires_assessment=True
        )
    elif func_lower == "fully_functional" and cond_lower == "working":
        results["Reuse"] = RouteEligibilityResult(
            route="Reuse",
            is_eligible=True,
            reason="The device is working and can remain in service without repair or transfer to another owner."
        )
    else:
        results["Reuse"] = RouteEligibilityResult(
            route="Reuse",
            is_eligible=False,
            reason="Continued use without repair is not recommended while functional issues remain."
        )
    # -------------------------------------------------------------
    # 3. RESELL ELIGIBILITY
    # -------------------------------------------------------------
    age = device.age_years if device.age_years is not None else 0
    max_resale_age = 7 if cat_lower in ["smartphone", "tablet"] else (10 if cat_lower in ["laptop", "desktop", "monitor"] else 5)
    
    if cat_lower == "charger":
        results["Resell"] = RouteEligibilityResult(
            route="Resell",
            is_eligible=False,
            reason="Standalone generic chargers have negligible secondary resale market value."
        )
    elif has_catastrophic_damage or (device.physically_damaged is True and overall_lower == "poor"):
        results["Resell"] = RouteEligibilityResult(
            route="Resell",
            is_eligible=False,
            reason="Severe physical damage or poor structural condition prevents standard secondary market resale."
        )
    elif device.powers_on is False and func_lower == "non_functional" and cond_lower == "not_working":
        results["Resell"] = RouteEligibilityResult(
            route="Resell",
            is_eligible=False,
            reason="Device does not power on and is completely non-functional; direct consumer resale is not feasible."
        )
    elif device.age_years is not None and device.age_years > max_resale_age:
        results["Resell"] = RouteEligibilityResult(
            route="Resell",
            is_eligible=False,
            reason=f"Device age ({device.age_years} years) exceeds standard consumer secondary market viability threshold ({max_resale_age} years)."
        )
    elif is_unknown_condition:
        results["Resell"] = RouteEligibilityResult(
            route="Resell",
            is_eligible=False,
            reason="Cannot list for resale without confirming power status and functional integrity."
        )
    else:
        results["Resell"] = RouteEligibilityResult(
            route="Resell",
            is_eligible=True,
            reason="Device meets power, functional baseline, and age parameters for consumer or wholesale resale."
        )

    # -------------------------------------------------------------
    # 4. DONATE ELIGIBILITY
    # -------------------------------------------------------------
    max_donation_age = 8 if cat_lower in ["smartphone", "tablet"] else 10
    
    if cat_lower == "charger":
        results["Donate"] = RouteEligibilityResult(
            route="Donate",
            is_eligible=False,
            reason="Standalone chargers are generally not accepted for institutional donation unless bundled with a device."
        )
    elif device.powers_on is False or func_lower == "non_functional" or cond_lower == "not_working":
        results["Donate"] = RouteEligibilityResult(
            route="Donate",
            is_eligible=False,
            reason="Charities, schools, and non-profits require devices that power on and can be placed in immediate service."
        )
    elif has_catastrophic_damage or (device.physically_damaged is True and overall_lower in ["poor", "fair"] and "screen_cracked" in faults_lower):
        results["Donate"] = RouteEligibilityResult(
            route="Donate",
            is_eligible=False,
            reason="Physical safety hazards (such as shattered glass or structural cracks) disqualify items from charitable donation."
        )
    elif device.age_years is not None and device.age_years > max_donation_age:
        results["Donate"] = RouteEligibilityResult(
            route="Donate",
            is_eligible=False,
            reason=f"Charities cannot accept devices older than {max_donation_age} years due to software incompatibility and lack of security updates."
        )
    elif is_unknown_condition:
        results["Donate"] = RouteEligibilityResult(
            route="Donate",
            is_eligible=False,
            reason="Donation partners require verified functional status before accepting equipment."
        )
    else:
        results["Donate"] = RouteEligibilityResult(
            route="Donate",
            is_eligible=True,
            reason="Device powers on with acceptable physical integrity, suitable for donation to educational or non-profit organizations."
        )

    # -------------------------------------------------------------
    # 5. REFURBISH ELIGIBILITY
    # -------------------------------------------------------------
    if cat_lower == "charger":
        results["Refurbish"] = RouteEligibilityResult(
            route="Refurbish",
            is_eligible=False,
            reason="Peripheral cables and chargers cannot be commercially refurbished."
        )
    elif has_catastrophic_damage:
        results["Refurbish"] = RouteEligibilityResult(
            route="Refurbish",
            is_eligible=False,
            reason="Catastrophic physical failure prevents professional restoration."
        )
    elif device.age_years is not None and device.age_years > 12:
        results["Refurbish"] = RouteEligibilityResult(
            route="Refurbish",
            is_eligible=False,
            reason="Hardware architecture is obsolete; replacement components are no longer commercially produced."
        )
    elif (cond_lower == "working" and func_lower == "fully_functional" and overall_lower in ["excellent", "good"] and len(faults_lower) == 0):
        results["Refurbish"] = RouteEligibilityResult(
            route="Refurbish",
            is_eligible=False,
            reason="Device is already in good or excellent working condition with no faults; comprehensive factory refurbishment is unnecessary."
        )
    elif is_unknown_condition:
        results["Refurbish"] = RouteEligibilityResult(
            route="Refurbish",
            is_eligible=True,
            reason="Professional refurbishment centers can perform diagnostic overhaul and parts testing.",
            requires_assessment=True
        )
    else:
        results["Refurbish"] = RouteEligibilityResult(
            route="Refurbish",
            is_eligible=True,
            reason="Device possesses restorable commercial value through parts overhaul, battery replacement, or certified testing."
        )

    # -------------------------------------------------------------
    # 6. RECYCLE ELIGIBILITY (Authorized E-Waste Recyclers)
    # -------------------------------------------------------------
    # Authorized e-waste recycling is ALWAYS feasible for all electronics
    results["Recycle"] = RouteEligibilityResult(
        route="Recycle",
        is_eligible=True,
        reason="Certified R2/e-Stewards recyclers accept all electronic devices for safe component recovery and hazardous materials handling."
    )

    eligible = [r for r, res in results.items() if res.is_eligible]
    ineligible = [r for r, res in results.items() if not res.is_eligible]

    guidance = ""
    if is_unknown_condition:
        guidance = "Device condition contains insufficient functional data. A professional bench assessment is strongly recommended."

    return StageAOutput(
        eligible_routes=eligible,
        ineligible_routes=ineligible,
        route_details=results,
        insufficient_info=is_unknown_condition,
        guidance_note=guidance
    )
