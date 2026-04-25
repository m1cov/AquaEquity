from dataclasses import dataclass

from app.services.estimation.crop_parameters import DEFAULT_CROPS, get_crop_parameters, normalize_crop_name


@dataclass(frozen=True)
class SoilCropParams:
    """
    Combined crop and soil parameters used by the EKF.

    FAO-style crop coefficients and depletion fractions come from crop metadata,
    while the root-zone storage bounds remain simplified estimator assumptions.
    All soil water quantities are mm of water in the crop root zone.
    """

    crop_name: str
    display_name: str
    soil_type: str
    theta_min: float
    theta_max: float
    theta_fc: float
    theta_wp: float
    drainage_coeff: float
    kc_initial: float
    kc_mid: float
    kc_late: float
    kc_min: float
    kc_max: float
    ndvi_to_kc_a: float
    ndvi_to_kc_b: float
    depletion_fraction_p: float
    irrigation_trigger_fraction: float
    irrigation_target_fraction: float
    max_irrigation_mm_day: float
    root_depth_m: float
    default_ndvi: float
    notes: str
    source_url: str


SOIL_MODIFIERS = {
    "loam": {
        "theta_max_factor": 1.00,
        "theta_fc_factor": 1.00,
        "theta_wp_factor": 1.00,
        "drainage_factor": 1.00,
    },
    "clay_loam": {
        "theta_max_factor": 1.12,
        "theta_fc_factor": 1.10,
        "theta_wp_factor": 1.08,
        "drainage_factor": 0.75,
    },
}


CROP_WATER_MODEL_PARAMS = {
    "tomato": {
        "theta_min": 0.0,
        "theta_max": 190.0,
        "theta_fc": 145.0,
        "theta_wp": 65.0,
        "drainage_coeff": 0.12,
        "max_irrigation_mm_day": 18.0,
    },
    "wheat": {
        "theta_min": 0.0,
        "theta_max": 180.0,
        "theta_fc": 140.0,
        "theta_wp": 60.0,
        "drainage_coeff": 0.10,
        "max_irrigation_mm_day": 14.0,
    },
    "maize": {
        "theta_min": 0.0,
        "theta_max": 185.0,
        "theta_fc": 145.0,
        "theta_wp": 62.0,
        "drainage_coeff": 0.11,
        "max_irrigation_mm_day": 16.0,
    },
}


DEFAULT_SOIL_TYPES = ["loam", "clay_loam"]


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _build_ndvi_to_kc(crop_default_ndvi: float, kc_initial: float, kc_mid: float) -> tuple[float, float]:
    ndvi_floor = 0.20
    ndvi_peak = max(crop_default_ndvi, ndvi_floor + 0.05)
    slope = (kc_mid - kc_initial) / (ndvi_peak - ndvi_floor)
    intercept = kc_initial - slope * ndvi_floor
    return slope, intercept


def get_crop_params(crop_name: str, soil_type: str = "loam") -> SoilCropParams:
    crop_key = normalize_crop_name(crop_name)
    soil_key = soil_type.strip().lower().replace(" ", "_")

    if soil_key not in SOIL_MODIFIERS:
        raise ValueError(f"Unsupported soil_type: {soil_type}")

    crop = get_crop_parameters(crop_key)
    base = dict(CROP_WATER_MODEL_PARAMS[crop.key])
    soil = SOIL_MODIFIERS[soil_key]

    base["theta_max"] *= soil["theta_max_factor"]
    base["theta_fc"] *= soil["theta_fc_factor"]
    base["theta_wp"] *= soil["theta_wp_factor"]
    base["drainage_coeff"] *= soil["drainage_factor"]

    ndvi_to_kc_a, ndvi_to_kc_b = _build_ndvi_to_kc(
        crop_default_ndvi=crop.default_ndvi,
        kc_initial=crop.kc_initial,
        kc_mid=crop.kc_mid,
    )
    trigger_fraction = _clamp(1.0 - crop.depletion_fraction_p, 0.15, 0.85)
    target_fraction = _clamp(trigger_fraction + 0.35, trigger_fraction + 0.10, 0.95)

    return SoilCropParams(
        crop_name=crop.key,
        display_name=crop.display_name,
        soil_type=soil_key,
        kc_initial=crop.kc_initial,
        kc_mid=crop.kc_mid,
        kc_late=crop.kc_late,
        kc_min=min(crop.kc_initial, crop.kc_late),
        kc_max=max(crop.kc_initial, crop.kc_mid, crop.kc_late),
        ndvi_to_kc_a=ndvi_to_kc_a,
        ndvi_to_kc_b=ndvi_to_kc_b,
        depletion_fraction_p=crop.depletion_fraction_p,
        irrigation_trigger_fraction=trigger_fraction,
        irrigation_target_fraction=target_fraction,
        root_depth_m=crop.root_depth_m,
        default_ndvi=crop.default_ndvi,
        notes=crop.notes,
        source_url=crop.source_url,
        **base,
    )
