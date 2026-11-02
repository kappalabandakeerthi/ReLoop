from dataclasses import dataclass
import re
from typing import List, Optional, Set, Tuple


REPLACEMENT_BENCHMARKS = {
    "laptop": 800.0, "smartphone": 600.0, "tablet": 450.0, "monitor": 250.0,
    "desktop": 900.0, "printer": 200.0, "charger": 35.0, "other": 300.0,
}
EXPECTED_SERVICE_LIFE = {
    "laptop": 5.0, "smartphone": 4.0, "tablet": 5.0, "monitor": 7.0,
    "desktop": 7.0, "printer": 6.0, "charger": 3.0, "other": 5.0,
}
CONDITION_MULTIPLIERS = {
    "excellent": 1.12, "good": 1.0, "fair": 0.76, "poor": 0.42, "unknown": 0.7,
}

FAULT_ALIASES = {
    "battery": ("battery", "cell failure", "not holding charge", "charge will not hold"),
    "screen": ("screen", "display", "lcd", "oled", "amoled", "retina", "digitizer", "panel", "cracked glass"),
    "motherboard": ("motherboard", "mainboard", "logic board", "system board", "board failure"),
    "charging_port": ("charging port", "charge port", "usb-c port", "usb port", "lightning port", "power jack"),
    "liquid_damage": ("liquid damage", "water damage", "corrosion"),
    "keyboard": ("keyboard", "keys stuck", "key failure"),
}

FAULT_REPAIR_RANGES = {
    "battery": {
        "laptop": (125, 280), "smartphone": (90, 230), "tablet": (95, 240), "monitor": (50, 130),
        "desktop": (45, 120), "printer": (45, 120), "charger": (15, 35), "other": (60, 170),
    },
    "screen": {
        "laptop": (210, 540), "smartphone": (145, 430), "tablet": (180, 470), "monitor": (130, 390),
        "desktop": (90, 240), "printer": (70, 190), "charger": (20, 45), "other": (120, 360),
    },
    "motherboard": {
        "laptop": (310, 760), "smartphone": (260, 690), "tablet": (250, 620), "monitor": (180, 480),
        "desktop": (260, 680), "printer": (150, 420), "charger": (35, 80), "other": (180, 520),
    },
    "charging_port": {
        "laptop": (105, 260), "smartphone": (70, 180), "tablet": (80, 200), "monitor": (65, 170),
        "desktop": (55, 150), "printer": (55, 155), "charger": (20, 45), "other": (70, 195),
    },
    "liquid_damage": {
        "laptop": (130, 360), "smartphone": (110, 340), "tablet": (120, 350), "monitor": (90, 260),
        "desktop": (100, 300), "printer": (80, 250), "charger": (20, 45), "other": (90, 290),
    },
    "keyboard": {
        "laptop": (85, 240), "smartphone": (0, 0), "tablet": (0, 0), "monitor": (0, 0),
        "desktop": (25, 100), "printer": (30, 115), "charger": (0, 0), "other": (35, 130),
    },
    "unknown": {
        "laptop": (90, 250), "smartphone": (75, 220), "tablet": (75, 220), "monitor": (70, 200),
        "desktop": (80, 230), "printer": (55, 170), "charger": (15, 40), "other": (60, 190),
    },
}
FAULT_RESALE_FACTORS = {
    "battery": 0.72, "screen": 0.48, "motherboard": 0.16, "charging_port": 0.68,
    "liquid_damage": 0.42, "keyboard": 0.78, "unknown": 0.62,
}
FAULT_LIFE_FACTORS = {
    "battery": 0.94, "screen": 0.9, "motherboard": 0.72, "charging_port": 0.95,
    "liquid_damage": 0.7, "keyboard": 0.96, "unknown": 0.82,
}
PREMIUM_MODEL_MARKERS = (
    " pro", " max", " ultra", "fold", "xps", "thinkpad x1", "macbook pro", "surface pro",
    "workstation", "gaming", "galaxy s", "iphone",
)
PREMIUM_DISPLAY_MARKERS = ("oled", "amoled", "retina", "mini-led", "mini led", "micro-led", "micro led")


@dataclass(frozen=True)
class AssessmentEstimate:
    estimated_repair_cost: float
    estimated_resale_value: float
    estimated_replacement_cost: float
    expected_remaining_life_years: float
    confidence: str
    notes: List[str]
    repair_cost_range: Tuple[float, float]
    replacement_cost_range: Tuple[float, float]
    resale_value_range: Tuple[float, float]
    remaining_life_range: Tuple[float, float]
    matched_faults: List[str]

    def ranges(self) -> dict:
        return {
            "estimated_repair_cost": {"low": self.repair_cost_range[0], "high": self.repair_cost_range[1]},
            "estimated_replacement_cost": {"low": self.replacement_cost_range[0], "high": self.replacement_cost_range[1]},
            "estimated_resale_value": {"low": self.resale_value_range[0], "high": self.resale_value_range[1]},
            "expected_remaining_life_years": {"low": self.remaining_life_range[0], "high": self.remaining_life_range[1]},
        }


def _classify_faults(specific_faults: List[str]) -> Tuple[Set[str], bool]:
    fault_types: Set[str] = set()
    has_unknown_fault = False
    for description in specific_faults:
        normalized = description.lower().replace("_", " ").replace("-", " ").strip()
        if not normalized:
            continue
        matches = {
            fault_type
            for fault_type, aliases in FAULT_ALIASES.items()
            if any(alias in normalized for alias in aliases)
        }
        if matches:
            fault_types.update(matches)
        else:
            has_unknown_fault = True
    if has_unknown_fault:
        fault_types.add("unknown")
    return fault_types, has_unknown_fault


def _model_cost_multiplier(brand: str, model: str) -> float:
    model_text = f" {brand} {model}".lower().strip()
    if any(marker in model_text for marker in PREMIUM_MODEL_MARKERS):
        return 1.28
    if any(marker in model_text for marker in ("chromebook", "entry level", "budget", " se ")):
        return 0.88
    if "apple" in brand.lower() or "macbook" in model_text or "iphone" in model_text:
        return 1.14
    return 1.0


def _display_cost_multiplier(model: str, specific_faults: List[str]) -> float:
    model_text = f"{model} {' '.join(specific_faults)}".lower().replace("_", " ").replace("-", " ")
    if "fold" in model_text:
        return 1.65
    if any(marker in model_text for marker in PREMIUM_DISPLAY_MARKERS):
        return 1.38
    return 1.0


def _display_type_known(model: str, specific_faults: List[str]) -> bool:
    model_text = f"{model} {' '.join(specific_faults)}".lower().replace("_", " ").replace("-", " ")
    return (
        "fold" in model_text
        or any(marker in model_text for marker in PREMIUM_DISPLAY_MARKERS)
        or bool(re.search(r"\blcd\b|\bled\b", model_text))
    )


def estimate_assessment_values(
    category: str,
    age_years: Optional[float],
    overall_condition: str,
    functional_status: str,
    specific_faults: List[str],
    physically_damaged: Optional[bool] = None,
    brand: str = "",
    model: str = "",
) -> AssessmentEstimate:
    """Estimate transparent fault-specific planning ranges, not market quotations."""
    requested_category = category.lower().strip()
    normalized_category = requested_category if requested_category in REPLACEMENT_BENCHMARKS else "other"
    expected_life = EXPECTED_SERVICE_LIFE[normalized_category]
    age = max(0.0, age_years if age_years is not None else expected_life * 0.6)
    condition = overall_condition.lower().strip()
    functional = functional_status.lower().strip()
    condition_multiplier = CONDITION_MULTIPLIERS.get(condition, CONDITION_MULTIPLIERS["unknown"])
    model_multiplier = _model_cost_multiplier(brand, model)
    replacement_cost = round(REPLACEMENT_BENCHMARKS[normalized_category] * model_multiplier, 2)
    fault_types, has_unknown_fault = _classify_faults(specific_faults)

    if not fault_types and functional in {"partially_functional", "non_functional", "unknown"}:
        fault_types.add("unknown")
        has_unknown_fault = True
    if not fault_types and physically_damaged:
        fault_types.add("unknown")
        has_unknown_fault = True

    component_ranges = []
    for fault_type in fault_types:
        base_low, base_high = FAULT_REPAIR_RANGES[fault_type][normalized_category]
        multiplier = model_multiplier * (1.0 + min(age, 12.0) * 0.012)
        multiplier *= 1.0 + max(0.0, 1.0 - condition_multiplier) * 0.18
        if physically_damaged and fault_type != "screen":
            multiplier *= 1.12
        if functional == "non_functional" and fault_type not in {"motherboard", "liquid_damage"}:
            multiplier *= 1.08
        if fault_type == "screen":
            multiplier *= _display_cost_multiplier(model, specific_faults)
        component_ranges.append((base_low * multiplier, base_high * multiplier))

    if not component_ranges:
        repair_low = repair_high = 0.0
    else:
        component_ranges.sort(key=lambda cost: cost[0] + cost[1], reverse=True)
        repair_low = component_ranges[0][0] + sum(low * 0.55 for low, _ in component_ranges[1:])
        repair_high = component_ranges[0][1] + sum(high * 0.55 for _, high in component_ranges[1:])
        repair_low = min(repair_low, replacement_cost * 1.1)
        repair_high = min(repair_high, replacement_cost * 1.1)
        if functional == "non_functional":
            repair_high = min(replacement_cost * 1.1, repair_high * 1.1)

    repair_range = (round(repair_low, 2), round(repair_high, 2))
    repair_cost = round(sum(repair_range) / 2.0, 2)

    depreciation = max(0.04, 0.78 * (0.84 ** age))
    resale_condition = condition_multiplier
    if functional == "non_functional":
        resale_condition = 0.12
    elif functional == "unknown":
        resale_condition *= 0.75
    resale_fault_factor = 1.0
    for fault_type in fault_types:
        resale_fault_factor *= FAULT_RESALE_FACTORS[fault_type]
    resale_value = round(replacement_cost * depreciation * resale_condition * resale_fault_factor, 2)

    remaining_life = max(0.0, expected_life - age) * condition_multiplier
    for fault_type in fault_types:
        remaining_life *= FAULT_LIFE_FACTORS[fault_type]
    if age <= expected_life and remaining_life > 0:
        remaining_life = max(0.5, remaining_life)
    remaining_life = round(min(expected_life, remaining_life), 1)

    display_info_missing = "screen" in fault_types and not _display_type_known(model, specific_faults)
    confidence = "low" if (
        requested_category not in REPLACEMENT_BENCHMARKS
        or condition == "unknown"
        or functional == "unknown"
        or age_years is None
        or has_unknown_fault
        or display_info_missing
    ) else "moderate"
    fault_names = sorted(fault_types)
    notes = [
        "Estimates are approximate planning ranges, not market quotations.",
        f"Replacement uses the {normalized_category} category benchmark and a {model_multiplier:.2f} brand/model tier factor.",
        f"Matched fault classes: {', '.join(fault_names) if fault_names else 'none reported'}.",
        "Distinct faults use separate part/labor bands; repeated or overlapping descriptions are counted once and secondary faults receive a reduced combined rate.",
        f"Remaining life starts from a {expected_life:.0f}-year category assumption and condition after repairable faults are addressed.",
    ]
    if "screen" in fault_types:
        notes.append(f"Display pricing uses a {_display_cost_multiplier(model, specific_faults):.2f} factor inferred from model and fault details.")
        if display_info_missing:
            notes.append("Display type could not be inferred; include LCD, OLED, AMOLED, or foldable details to narrow the screen range.")
    if has_unknown_fault:
        notes.append("At least one fault is unclassified; a broad diagnostic range is used and more detail would improve confidence.")
    if confidence == "low":
        notes.append("More precise model, age, condition, and fault details would narrow these estimates.")

    return AssessmentEstimate(
        estimated_repair_cost=repair_cost,
        estimated_resale_value=resale_value,
        estimated_replacement_cost=replacement_cost,
        expected_remaining_life_years=remaining_life,
        confidence=confidence,
        notes=notes,
        repair_cost_range=repair_range,
        replacement_cost_range=(round(replacement_cost * 0.9, 2), round(replacement_cost * 1.15, 2)),
        resale_value_range=(round(resale_value * 0.8, 2), round(resale_value * 1.2, 2)),
        remaining_life_range=(round(max(0.0, remaining_life - 0.5), 1), round(min(expected_life, remaining_life + 0.5), 1)),
        matched_faults=fault_names,
    )
