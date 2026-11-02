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
    RouteEligibilityResult,
    ROUTES,
    evaluate_recovery_eligibility
)
from app.engine.scoring import (
    ScoringWeights,
    score_eligible_routes
)
from app.engine.recommender import (
    run_reloop_recommendation_pipeline
)
from app.engine.assessment_estimator import estimate_assessment_values

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
    assert result.recommended_route in ["Reuse", "Resell", "Donate"]
    assert result.overall_score >= 70.0
    assert "Reuse" in stage_a.eligible_routes
    # Financial score is the actual resale-to-replacement ratio.
    assert result.all_scores["Resell"].financial_score == pytest.approx(47.5)

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
    assert result.recommended_route in ["Reuse", "Resell", "Donate"]
    # Check that financial score is NOT arbitrarily 0.0
    resell_fin = result.all_scores["Resell"].financial_score
    assert resell_fin > 25.0, f"Expected non-zero imputed financial score, got {resell_fin}"

def test_reuse_route_ranks_fully_functional_device():
    device = DeviceAssessmentInput(
        category="Laptop",
        age_years=2.0,
        working_condition="working",
        functional_status="fully_functional",
        overall_condition="good",
        powers_on=True,
    )

    result = run_reloop_recommendation_pipeline(device)

    assert result.recommended_route == "Reuse"
    assert "continuing to use" in result.explanation.lower()
    assert result.all_scores["Reuse"].breakdown["weights"] == result.weights_used

def test_assessment_estimator_uses_category_age_and_condition():
    estimate = estimate_assessment_values(
        category="Laptop",
        age_years=3.0,
        overall_condition="good",
        functional_status="partially_functional",
        specific_faults=["battery_drain"],
    )

    assert estimate.estimated_replacement_cost == 800.0
    assert estimate.estimated_repair_cost > 0
    assert estimate.estimated_resale_value > 0
    assert estimate.expected_remaining_life_years > 0
    assert estimate.confidence == "moderate"
    assert "not market quotations" in " ".join(estimate.notes).lower()

def test_fault_specific_costs_differ_for_battery_screen_board_and_port():
    faults = {
        "battery": "Battery failure",
        "screen": "Cracked OLED display",
        "motherboard": "Motherboard failure",
        "charging_port": "Charging port failure",
    }
    estimates = {
        fault_type: estimate_assessment_values(
            category="Smartphone",
            brand="Apple",
            model="iPhone 14 OLED",
            age_years=2,
            overall_condition="good",
            functional_status="partially_functional",
            specific_faults=[description],
        )
        for fault_type, description in faults.items()
    }

    midpoints = {fault_type: estimate.estimated_repair_cost for fault_type, estimate in estimates.items()}
    assert len(set(midpoints.values())) == 4
    assert midpoints["motherboard"] > midpoints["screen"] > midpoints["battery"] > midpoints["charging_port"]
    assert estimates["battery"].matched_faults == ["battery"]
    assert estimates["screen"].repair_cost_range[1] > estimates["screen"].repair_cost_range[0]
    assert estimates["motherboard"].estimated_repair_cost > estimates["motherboard"].estimated_replacement_cost * 0.5

def test_screen_estimate_uses_display_type_and_exact_model_tier():
    oled = estimate_assessment_values(
        category="Laptop", brand="Acme", model="Book 14 OLED", age_years=2,
        overall_condition="good", functional_status="partially_functional",
        specific_faults=["cracked screen"],
    )
    lcd = estimate_assessment_values(
        category="Laptop", brand="Acme", model="Book 14 LCD", age_years=2,
        overall_condition="good", functional_status="partially_functional",
        specific_faults=["cracked screen"],
    )
    premium_board = estimate_assessment_values(
        category="Laptop", brand="Lenovo", model="ThinkPad X1 Pro", age_years=2,
        overall_condition="good", functional_status="partially_functional",
        specific_faults=["motherboard failure"],
    )
    standard_board = estimate_assessment_values(
        category="Laptop", brand="Lenovo", model="IdeaPad 3", age_years=2,
        overall_condition="good", functional_status="partially_functional",
        specific_faults=["motherboard failure"],
    )

    assert oled.estimated_repair_cost > lcd.estimated_repair_cost
    assert premium_board.estimated_repair_cost > standard_board.estimated_repair_cost

def test_multiple_faults_combine_without_duplicate_charges():
    single_battery = estimate_assessment_values(
        category="Laptop", brand="Acme", model="Book 14", age_years=3,
        overall_condition="good", functional_status="partially_functional",
        specific_faults=["battery failure"],
    )
    repeated_battery = estimate_assessment_values(
        category="Laptop", brand="Acme", model="Book 14", age_years=3,
        overall_condition="good", functional_status="partially_functional",
        specific_faults=["battery failure", "battery not holding charge"],
    )
    battery_and_port = estimate_assessment_values(
        category="Laptop", brand="Acme", model="Book 14", age_years=3,
        overall_condition="good", functional_status="partially_functional",
        specific_faults=["battery failure", "charging port failure"],
    )

    assert repeated_battery.repair_cost_range == single_battery.repair_cost_range
    assert repeated_battery.matched_faults == ["battery"]
    assert battery_and_port.estimated_repair_cost > single_battery.estimated_repair_cost
    assert battery_and_port.repair_cost_range[1] < single_battery.repair_cost_range[1] + estimate_assessment_values(
        category="Laptop", brand="Acme", model="Book 14", age_years=3,
        overall_condition="good", functional_status="partially_functional",
        specific_faults=["charging port failure"],
    ).repair_cost_range[1]

def test_age_condition_function_and_unknown_fault_change_estimate_and_confidence():
    functional_battery = estimate_assessment_values(
        category="Smartphone", brand="Acme", model="Phone 12", age_years=2,
        overall_condition="good", functional_status="fully_functional",
        specific_faults=["battery failure"],
    )
    nonfunctional_battery = estimate_assessment_values(
        category="Smartphone", brand="Acme", model="Phone 12", age_years=2,
        overall_condition="good", functional_status="non_functional",
        specific_faults=["battery failure"],
    )
    healthy_battery = estimate_assessment_values(
        category="Smartphone", brand="Acme", model="Phone 12", age_years=1,
        overall_condition="good", functional_status="partially_functional",
        specific_faults=["battery failure"],
    )
    old_damaged_battery = estimate_assessment_values(
        category="Smartphone", brand="Acme", model="Phone 12", age_years=4,
        overall_condition="poor", functional_status="non_functional",
        specific_faults=["battery failure"], physically_damaged=True,
    )
    unknown_fault = estimate_assessment_values(
        category="Smartphone", brand="Acme", model="Phone 12", age_years=2,
        overall_condition="good", functional_status="partially_functional",
        specific_faults=["intermittent mystery fault"],
    )

    assert nonfunctional_battery.estimated_repair_cost > functional_battery.estimated_repair_cost
    assert old_damaged_battery.estimated_repair_cost > healthy_battery.estimated_repair_cost
    assert old_damaged_battery.estimated_resale_value < healthy_battery.estimated_resale_value
    assert old_damaged_battery.expected_remaining_life_years < healthy_battery.expected_remaining_life_years
    assert unknown_fault.confidence == "low"
    assert "unknown" in unknown_fault.matched_faults

def test_required_fault_types_have_distinct_repair_ranges():
    fault_descriptions = {
        "battery": "Battery failure",
        "screen": "Cracked OLED display",
        "motherboard": "Motherboard failure",
        "charging_port": "Charging port failure",
    }
    estimates = {
        fault_type: estimate_assessment_values(
            category="Smartphone",
            brand="Acme",
            model="Phone 14",
            age_years=2,
            overall_condition="good",
            functional_status="partially_functional",
            specific_faults=[description],
        )
        for fault_type, description in fault_descriptions.items()
    }

    repair_midpoints = {kind: estimate.estimated_repair_cost for kind, estimate in estimates.items()}
    assert len(set(repair_midpoints.values())) == 4
    assert repair_midpoints["motherboard"] > repair_midpoints["screen"]
    assert repair_midpoints["screen"] > repair_midpoints["battery"]
    assert repair_midpoints["battery"] > repair_midpoints["charging_port"]
    assert estimates["motherboard"].estimated_repair_cost > estimates["motherboard"].estimated_replacement_cost * 0.5

def test_display_technology_and_exact_model_change_screen_range():
    oled = estimate_assessment_values(
        category="Laptop", brand="Acme", model="Book 14", age_years=2,
        overall_condition="good", functional_status="partially_functional",
        specific_faults=["cracked OLED screen"],
    )
    lcd = estimate_assessment_values(
        category="Laptop", brand="Acme", model="Book 14", age_years=2,
        overall_condition="good", functional_status="partially_functional",
        specific_faults=["cracked LCD screen"],
    )
    unknown_display = estimate_assessment_values(
        category="Laptop", brand="Acme", model="Book 14", age_years=2,
        overall_condition="good", functional_status="partially_functional",
        specific_faults=["cracked screen"],
    )
    premium_model = estimate_assessment_values(
        category="Laptop", brand="Lenovo", model="ThinkPad X1 Pro OLED", age_years=2,
        overall_condition="good", functional_status="partially_functional",
        specific_faults=["cracked screen"],
    )

    assert oled.estimated_repair_cost > lcd.estimated_repair_cost
    assert premium_model.estimated_repair_cost > oled.estimated_repair_cost
    assert unknown_display.confidence == "low"
    assert any("Display type could not be inferred" in note for note in unknown_display.notes)

def test_all_six_route_scores_respond_to_device_fault_profile():
    functional_device = DeviceAssessmentInput(
        category="Laptop", brand="Acme", model="Book 14", age_years=1,
        working_condition="working", functional_status="fully_functional",
        overall_condition="good", powers_on=True,
    )
    faulted_device = DeviceAssessmentInput(
        category="Laptop", brand="Acme", model="Book 14", age_years=4,
        working_condition="not_working", functional_status="non_functional",
        overall_condition="poor", powers_on=False, physically_damaged=True,
        specific_faults=["motherboard failure", "cracked screen"],
    )
    eligible = {
        route: RouteEligibilityResult(route=route, is_eligible=True, reason="test profile")
        for route in ROUTES
    }

    functional_scores = score_eligible_routes(functional_device, eligible)
    faulted_scores = score_eligible_routes(faulted_device, eligible)

    assert set(functional_scores) == {"Repair", "Reuse", "Resell", "Donate", "Refurbish", "Recycle"}
    for route in ROUTES:
        assert functional_scores[route].final_score != faulted_scores[route].final_score
        assert 0 <= faulted_scores[route].final_score <= 100
