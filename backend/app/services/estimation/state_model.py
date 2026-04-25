import numpy as np

from app.services.estimation.evapotranspiration import clamp
from app.services.estimation.parameters import SoilCropParams


def kc_from_ndvi(ndvi: float, params: SoilCropParams) -> float:
    kc = params.ndvi_to_kc_a * ndvi + params.ndvi_to_kc_b
    return clamp(kc, params.kc_min, params.kc_max)


def water_stress_coefficient(theta: float, params: SoilCropParams) -> float:
    if theta <= params.theta_wp:
        return 0.0
    if theta >= params.theta_fc:
        return 1.0
    return (theta - params.theta_wp) / (params.theta_fc - params.theta_wp)


def drainage(theta: float, params: SoilCropParams) -> float:
    excess = max(theta - params.theta_fc, 0.0)
    return params.drainage_coeff * excess


def actual_evapotranspiration(et0: float, ndvi: float, theta: float, params: SoilCropParams) -> float:
    return et0 * kc_from_ndvi(ndvi, params) * water_stress_coefficient(theta, params)


def available_water(theta: float, params: SoilCropParams) -> float:
    taw = params.theta_fc - params.theta_wp
    return clamp(theta - params.theta_wp, 0.0, taw)


def relative_available_water(theta: float, params: SoilCropParams) -> float:
    taw = params.theta_fc - params.theta_wp
    if taw <= 0:
        return 0.0
    return available_water(theta, params) / taw


def stress_level(theta: float, params: SoilCropParams) -> str:
    rel_aw = relative_available_water(theta, params)
    if rel_aw < 0.20:
        return "critical"
    if rel_aw < params.irrigation_trigger_fraction:
        return "high"
    if rel_aw < 0.70:
        return "moderate"
    return "low"


def irrigation_control(theta: float, params: SoilCropParams) -> float:
    taw = params.theta_fc - params.theta_wp
    aw = available_water(theta, params)
    trigger_aw = params.irrigation_trigger_fraction * taw
    target_aw = params.irrigation_target_fraction * taw

    if aw < trigger_aw:
        return clamp(target_aw - aw, 0.0, params.max_irrigation_mm_day)

    return 0.0


def f_state(x: np.ndarray, u: dict, params: SoilCropParams) -> np.ndarray:
    """
    State equation:
        theta[k+1] = theta[k] + rain + irrigation - ETa - drainage
    """
    theta = float(x[0])
    rain = float(u.get("rain_mm", 0.0))
    irrigation = float(u.get("irrigation_mm", 0.0))
    et0 = float(u.get("et0_mm", 0.0))
    ndvi = float(u.get("ndvi", 0.65))

    eta = actual_evapotranspiration(et0, ndvi, theta, params)
    d = drainage(theta, params)

    theta_next = theta + rain + irrigation - eta - d
    theta_next = clamp(theta_next, params.theta_min, params.theta_max)

    return np.array([theta_next], dtype=float)


def F_jacobian(x: np.ndarray, u: dict, params: SoilCropParams, eps: float = 1e-5) -> np.ndarray:
    x = x.astype(float)
    fx = f_state(x, u, params)
    x_perturbed = x.copy()
    x_perturbed[0] += eps
    fx_perturbed = f_state(x_perturbed, u, params)
    return ((fx_perturbed - fx) / eps).reshape(1, 1)
