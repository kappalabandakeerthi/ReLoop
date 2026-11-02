"""
ReLoop Decision Engine Unit Tests
Validates all mandatory scenarios and engine guarantees:
- Scenario A: Functional laptop with battery issue (Repair prioritized)
- Scenario B: Functional smartphone that is no longer needed (Resell or Donate prioritized)
- Scenario C: Severely damaged monitor (Authorized recycling / assessment prioritized)
- Scenario D: Device with insufficient condition information (Diagnostic assessment fallback)
- Weight configurability
- Missing data handling (no arbitrary zeros, contextual imputation)
- Eligibility and scoring separation
"""

import pytest
from app.engine.eligibility import (
    DeviceAssessmentInput,
    evaluate_recovery_eligibility
)
from app.engine.scoring import (
    ScoringWeights,
    score_eligible_routes
)
from app.engine.recommender import (
    run_reloop_recommendation_pipeline
)

# -------------------------------------------------------------
# Scenario A: Functional laptop with battery issue
# Expected: Repair should be considered if economically sensible
# -------------------------------------------------------------
def test_scenario_a_laptop_battery_repair():
    laptop_input = DeviceAssessmentInput(
        category="Laptop",
        brand="Dell",
        model="XPS 13",
        age_years=3.0,
        working_condition="minor_issues",
        functional_status="partially_functional",
        overall_condition="good",
        powers_on=True,
        physically_damaged=False,
        specific_faults=["battery_drain", "battery_not_holding_charge"],
        estimated_repair_cost=85.0, # affordable battery replacement
        estimated_replacement_cost=1100.0,
        expected_remaining_life_years=3.5
    )

    stage_a = evaluate_recovery_eligibility(laptop_input)
    assert "Repair" in stage_a.eligible_routes, "Repair must be eligible for serviceable battery issue"

    result = run_reloop_recommendation_pipeline(laptop_input)
    assert result.recommended_route == "Repair", f"Expected Repair as #1 route, got {result.recommended_route}"
    assert result.overall_score >= 70.0
    assert result.all_scores["Repair"].financial_score >= 80.0
    assert "battery" in result.all_scores["Repair"].breakdown["evaluation_notes"][0].lower() or "repair" in result.all_scores["Repair"].breakdown["evaluation_notes"][0].lower()

# -------------------------------------------------------------
# Scenario B: Functional smartphone that is no longer needed
# Expected: Resell or Donate should be considered
# -------------------------------------------------------------
def test_scenario_b_functional_smartphone_resell_or_donate():
    phone_input = DeviceAssessmentInput(
        category="Smartphone",
        brand="Apple",
        model="iPhone 13",
        age_years=2.0,
        working_condition="working",
        functional_status="fully_functional",
        overall_condition="excellent",
        powers_on=True,
        physically_damaged=False,
        specific_faults=[],
        estimated_resale_value=380.0,
        estimated_replacement_cost=800.0,
        expected_remaining_life_years=3.0
    )

    stage_a = evaluate_recovery_eligibility(phone_input)
    # Device is fully functional without faults, so Repair is ineligible/not needed
    assert "Repair" not in stage_a.eligible_routes
    assert "Resell" in stage_a.eligible_routes
    assert "Donate" in stage_a.eligible_routes

    result = run_reloop_recommendation_pipeline(phone_input)
    assert result.recommended_route in ["Resell", "Donate"]
    assert result.overall_score >= 70.0
    # Resell should have high financial return
    assert result.all_scores["Resell"].financial_score >= 60.0

# -------------------------------------------------------------
# Scenario C: Severely damaged monitor
# Expected: Professional assessment or authorized recycling
# -------------------------------------------------------------
def test_scenario_c_severely_damaged_monitor():
    monitor_input = DeviceAssessmentInput(
        category="Monitor",
        brand="LG",
        model="UltraGear 27",
        age_years=4.0,
        working_condition="not_working",
        functional_status="non_functional",
        overall_condition="poor",
        powers_on=False,
        physically_damaged=True,
        specific_faults=["crushed", "shattered_panel_and_chassis", "internal_component_fracture"],
        estimated_repair_cost=280.0, # repair exceeds monitor value
        estimated_replacement_cost=250.0
    )

    stage_a = evaluate_recovery_eligibility(monitor_input)
    assert "Repair" not in stage_a.eligible_routes, "Catastrophic damage must disqualify Repair"
    assert "Resell" not in stage_a.eligible_routes, "Severe damage must disqualify Resell"
    assert "Donate" not in stage_a.eligible_routes, "Unusable/hazardous monitor cannot be donated"
    assert "Recycle" in stage_a.eligible_routes, "Recycle must always be eligible"

    result = run_reloop_recommendation_pipeline(monitor_input)
    assert result.recommended_route == "Recycle", f"Expected Recycle for shattered monitor, got {result.recommended_route}"
    assert result.all_scores["Recycle"].is_eligible is True

# -------------------------------------------------------------
# Scenario D: Device with insufficient condition information
# Expected: Request further information or professional assessment
# -------------------------------------------------------------
def test_scenario_d_insufficient_information():
    unknown_input = DeviceAssessmentInput(
        category="Laptop",
        brand="Lenovo",
        model="ThinkPad",
        working_condition="unknown",
        functional_status="unknown",
        overall_condition="unknown",
        powers_on=None, # unknown
        physically_damaged=None,
        specific_faults=[]
    )

    stage_a = evaluate_recovery_eligibility(unknown_input)
    assert stage_a.insufficient_info is True
    assert stage_a.route_details["Repair"].requires_assessment is True

    result = run_reloop_recommendation_pipeline(unknown_input)
    assert result.is_fallback is True
    assert result.fallback_message is not None
    assert "assessment" in result.fallback_message.lower()

# -------------------------------------------------------------
# Test Configurable Weights
# -------------------------------------------------------------
def test_configurable_weights():
    device = DeviceAssessmentInput(
        category="Laptop",
        brand="HP",
        working_condition="minor_issues",
        functional_status="partially_functional",
        overall_condition="fair",
        powers_on=True,
        specific_faults=["keyboard_keys_stuck"],
        estimated_repair_cost=50.0,
        estimated_replacement_cost=600.0
    )

    # Favor Convenience (e.g. 70% convenience)
    weights_convenience = ScoringWeights(
        financial=0.10,
        useful_life=0.10,
        convenience=0.70,
        reuse=0.10
    )
    res_conv = run_reloop_recommendation_pipeline(device, weights_convenience)
    assert res_conv.weights_used["convenience"] == 0.70

    # Favor Financial (e.g. 80% financial)
    weights_fin = ScoringWeights(
        financial=0.80,
        useful_life=0.10,
        convenience=0.05,
        reuse=0.05
    )
    res_fin = run_reloop_recommendation_pipeline(device, weights_fin)
    assert res_fin.weights_used["financial"] == 0.80

# -------------------------------------------------------------
# Test Missing Data Handling
# -------------------------------------------------------------
def test_missing_data_does_not_zero_scores():
    device = DeviceAssessmentInput(
        category="Tablet",
        brand="Samsung",
        model="Galaxy Tab",
        age_years=2.0,
        working_condition="working",
        functional_status="fully_functional",
        overall_condition="good",
        powers_on=True,
        # No cost or financial estimates supplied by user:
        estimated_repair_cost=None,
        estimated_resale_value=None,
        estimated_replacement_cost=None,
        expected_remaining_life_years=None
    )

    result = run_reloop_recommendation_pipeline(device)
    assert result.recommended_route in ["Resell", "Donate"]
    # Check that financial score is NOT arbitrarily 0.0
    resell_fin = result.all_scores["Resell"].financial_score
    assert resell_fin > 25.0, f"Expected non-zero imputed financial score, got {resell_fin}"
