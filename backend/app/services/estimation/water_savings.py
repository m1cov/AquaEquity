from dataclasses import dataclass

from app.services.estimation.crop_parameters import DEFAULT_CROPS, normalize_crop_name


STRESS_DEFINITION = (
    "This MVP estimates water savings while assuming crop stress refers only to water stress "
    "and that fertility, pests, disease, and soil management are normal."
)


@dataclass(frozen=True)
class BaselineIrrigationProfile:
    strategy: str
    baseline_mm_month_low: float
    baseline_mm_month_typical: float
    baseline_mm_month_high: float
    explanation: str


BASELINE_IRRIGATION_PROFILES = {
    "wheat": BaselineIrrigationProfile(
        strategy="rainfed_or_supplemental",
        baseline_mm_month_low=0.0,
        baseline_mm_month_typical=40.0,
        baseline_mm_month_high=80.0,
        explanation="Wheat is often rain-fed, but may receive supplemental irrigation in dry periods.",
    ),
    "maize": BaselineIrrigationProfile(
        strategy="moderate_irrigation",
        baseline_mm_month_low=100.0,
        baseline_mm_month_typical=150.0,
        baseline_mm_month_high=220.0,
        explanation="Maize usually needs moderate irrigation support during hot, dry summer growth.",
    ),
    "tomato": BaselineIrrigationProfile(
        strategy="intensive_irrigation",
        baseline_mm_month_low=160.0,
        baseline_mm_month_typical=220.0,
        baseline_mm_month_high=300.0,
        explanation="Tomato is commonly managed with intensive irrigation because yield and quality are sensitive to water stress.",
    ),
}


def mm_to_liters(mm: float, field_area_m2: float) -> float:
    """Convert irrigation depth to volume: 1 mm over 1 m2 equals 1 liter."""
    return float(mm) * float(field_area_m2)


def _round_mm(value: float) -> float:
    return round(float(value), 2)


def _round_liters(value: float) -> float:
    return round(float(value), 2)


def _baseline_mm_for_mode(profile: BaselineIrrigationProfile, baseline_mode: str) -> float:
    if baseline_mode == "low":
        return profile.baseline_mm_month_low
    if baseline_mode == "typical":
        return profile.baseline_mm_month_typical
    if baseline_mode == "high":
        return profile.baseline_mm_month_high
    raise ValueError("Invalid baseline_mode. Available modes: low, typical, high")


def estimate_water_savings(
    crop_name: str,
    field_area_m2: float,
    smart_irrigation_mm_month: float,
    baseline_mode: str = "typical",
) -> dict:
    if field_area_m2 <= 0:
        raise ValueError("field_area_m2 must be greater than 0.")

    if smart_irrigation_mm_month < 0:
        raise ValueError("smart_irrigation_mm_month must be greater than or equal to 0.")

    crop_key = normalize_crop_name(crop_name)
    if crop_key not in BASELINE_IRRIGATION_PROFILES:
        raise ValueError(f"Unknown crop '{crop_name}'. Available crops: {', '.join(DEFAULT_CROPS)}")

    profile = BASELINE_IRRIGATION_PROFILES[crop_key]
    baseline_mode_key = baseline_mode.strip().lower()
    baseline_mm = _baseline_mm_for_mode(profile, baseline_mode_key)
    smart_mm = float(smart_irrigation_mm_month)
    saved_mm = max(baseline_mm - smart_mm, 0.0)

    baseline_liters = mm_to_liters(baseline_mm, field_area_m2)
    smart_liters = mm_to_liters(smart_mm, field_area_m2)
    saved_liters = mm_to_liters(saved_mm, field_area_m2)
    saved_percent = 0.0 if baseline_mm <= 0 or saved_mm <= 0 else (saved_mm / baseline_mm) * 100.0

    return {
        "crop_name": crop_key,
        "baseline_mode": baseline_mode_key,
        "baseline_irrigation_mm_month": _round_mm(baseline_mm),
        "smart_irrigation_mm_month": _round_mm(smart_mm),
        "water_saved_mm_month": _round_mm(saved_mm),
        "baseline_irrigation_liters_month": _round_liters(baseline_liters),
        "smart_irrigation_liters_month": _round_liters(smart_liters),
        "water_saved_liters_month": _round_liters(saved_liters),
        "water_saved_percent": round(saved_percent, 2),
        "strategy": profile.strategy,
        "explanation": profile.explanation,
        "stress_definition": STRESS_DEFINITION,
    }


def estimate_worst_case_monthly_quota(
    field_area_m2: float,
    et0_hot_day_mm: float,
    kc_peak: float,
    days: int = 30,
) -> dict:
    if field_area_m2 <= 0:
        raise ValueError("field_area_m2 must be greater than 0.")

    worst_case_mm = float(days) * float(et0_hot_day_mm) * float(kc_peak)
    worst_case_liters = mm_to_liters(worst_case_mm, field_area_m2)

    return {
        "worst_case_mm_month": _round_mm(worst_case_mm),
        "worst_case_liters_month": _round_liters(worst_case_liters),
    }
