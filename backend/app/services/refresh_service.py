"""
Refresh service.

Replaces what used to be Supabase's `refresh-farm-data` edge function.
For each farm in MySQL it:
  1. Loads (or initializes) the farm's EKF state.
  2. Pulls weather + Sentinel-2 stats (best effort — falls back to defaults).
  3. Runs one EKF day step.
  4. Converts the soil-water estimate into the % units the frontend uses.
  5. Persists a new FarmReading row.
  6. Creates alerts where appropriate.
"""
from __future__ import annotations

from datetime import date as Date
from typing import Optional

from sqlalchemy.orm import Session

from app.db_models import Alert, Farm, FarmReading
from app.schemas import RefreshResponse
from app.services.alert_service import evaluate_and_create_alerts
from app.services.estimation.estimator_service import estimator_service
from app.services.estimation.parameters import get_crop_params
from app.services.estimation.state_model import (
    relative_available_water,
    stress_level,
)
from app.services.weather.weather_client import fetch_weather

# In-memory cache of EKF instances per farm. Keyed by farm.id. Hot state lives
# here between requests; cold state survives in the DB as the last reading.
_ekf_cache: dict[str, object] = {}


def _stress_to_frontend(level: str) -> str:
    """
    EKF returns one of: low, moderate, high, critical.
    Frontend uses: healthy, moderate, stressed.
    """
    mapping = {
        "low": "healthy",
        "moderate": "moderate",
        "high": "stressed",
        "critical": "stressed",
    }
    return mapping.get(level, "moderate")


def _soil_water_mm_to_pct(soil_water_mm: float, params) -> float:
    """
    Convert EKF soil-water [mm in root zone] to a % display value the frontend
    expects. We map the wilting-point/field-capacity range to 0-100%.
    """
    span = float(params.theta_max) - float(params.theta_wp)
    if span <= 0:
        return 0.0
    pct = (soil_water_mm - float(params.theta_wp)) / span * 100.0
    return max(0.0, min(100.0, pct))


def _farm_polygon(farm: Farm) -> dict:
    """
    Build a small GeoJSON polygon around the farm's centroid so the Sentinel
    Statistical API and Open-Meteo helpers have something to work with.
    Uses a square sized from size_ha.
    """
    import math

    area_m2 = float(farm.size_ha) * 10000
    side = math.sqrt(area_m2)
    d_lat = (side / 2) / 111_320
    d_lng = (side / 2) / (111_320 * max(0.1, math.cos(math.radians(float(farm.latitude)))))
    lat = float(farm.latitude)
    lng = float(farm.longitude)
    ring = [
        [lng - d_lng, lat - d_lat],
        [lng + d_lng, lat - d_lat],
        [lng + d_lng, lat + d_lat],
        [lng - d_lng, lat + d_lat],
        [lng - d_lng, lat - d_lat],
    ]
    return {"type": "Polygon", "coordinates": [ring]}


def _initial_soil_water_mm(farm: Farm, db: Session) -> float:
    """
    Bootstrap the EKF with the most-recent persisted reading if available, else
    a sensible default based on the crop's params.
    """
    latest = (
        db.query(FarmReading)
        .filter(FarmReading.farm_id == farm.id)
        .order_by(FarmReading.fetched_at.desc())
        .first()
    )
    params = get_crop_params(farm.crop_name, farm.soil_type)
    if latest is None or latest.soil_moisture_pct is None:
        # Start halfway between WP and FC
        return float(params.theta_wp) + 0.5 * (float(params.theta_fc) - float(params.theta_wp))

    pct = float(latest.soil_moisture_pct)
    span = float(params.theta_max) - float(params.theta_wp)
    return float(params.theta_wp) + (pct / 100.0) * span


def _recommended_window(liters: float) -> tuple[str, str]:
    """Mirror the frontend's recommendedWindow() logic for consistency."""
    flow_l_per_h = 8000.0
    hours = max(0.5, min(4.0, liters / flow_l_per_h)) if liters > 0 else 0.0
    start_h = 4.0
    end_h = start_h + hours

    def fmt(h: float) -> str:
        hh = int(h)
        mm = int(round((h - hh) * 60))
        return f"{hh:02d}:{mm:02d}"

    return fmt(start_h), fmt(end_h)


def _liters_for_recommendation(rec_irrigation_mm: float, farm: Farm) -> float:
    """1 mm over 1 m² == 1 L. Multiply by farm area."""
    area_m2 = float(farm.size_ha) * 10000
    return rec_irrigation_mm * area_m2


def refresh_one_farm(db: Session, farm: Farm) -> tuple[Optional[FarmReading], list[Alert]]:
    """
    Run a refresh cycle for a single farm and persist a new FarmReading.
    Returns (reading, new_alerts). The caller is responsible for db.commit().
    """
    try:
        params = get_crop_params(farm.crop_name, farm.soil_type)
    except ValueError:
        # Unknown crop; skip but don't fail the whole cycle.
        return None, []

    # Get-or-create EKF
    ekf = _ekf_cache.get(farm.id)
    if ekf is None:
        ekf = estimator_service.create_filter(
            initial_soil_water_mm=_initial_soil_water_mm(farm, db)
        )
        _ekf_cache[farm.id] = ekf

    geometry = _farm_polygon(farm)
    today = Date.today().isoformat()

    # Best-effort fetch — weather has a fallback, sentinel may return None
    try:
        weather = fetch_weather(geometry, today)
    except Exception:
        weather = {"rain_mm": 0.0, "et0_mm": 5.0, "weather_source": "fallback"}

    # Run a daily EKF step. The estimator handles satellite internally if creds
    # are configured, else gracefully degrades to weather-only prediction.
    try:
        result = estimator_service.run_daily_step(
            ekf=ekf,
            params=params,
            field_geometry=geometry,
            date=today,
            weather=weather,
            auto_irrigate=True,
        )
    except Exception:
        # Don't let one bad farm break the whole refresh
        return None, []

    soil_water_mm = float(result["x_upd"])
    soil_pct = _soil_water_mm_to_pct(soil_water_mm, params)
    ndvi = result.get("ndvi_mean")
    if ndvi is None:
        ndvi = float(params.default_ndvi)

    rec_liters = _liters_for_recommendation(float(result["irrigation_mm"]), farm)
    win_start, win_end = _recommended_window(rec_liters)
    raw_stress = stress_level(soil_water_mm, params)
    fe_stress = _stress_to_frontend(raw_stress)

    reading = FarmReading(
        farm_id=farm.id,
        ndvi=round(float(ndvi), 3),
        soil_moisture_pct=round(soil_pct, 2),
        recommended_water_liters=round(rec_liters, 2),
        recommended_window_start=win_start,
        recommended_window_end=win_end,
        stress_level=fe_stress,
    )
    db.add(reading)
    db.flush()  # populate reading.id without committing yet

    new_alerts = evaluate_and_create_alerts(db, farm, reading)
    return reading, new_alerts


def refresh_all_farms(db: Session) -> RefreshResponse:
    farms = db.query(Farm).all()
    new_readings = 0
    new_alerts = 0
    for farm in farms:
        reading, alerts = refresh_one_farm(db, farm)
        if reading is not None:
            new_readings += 1
        new_alerts += len(alerts)

    db.commit()
    return RefreshResponse(
        refreshed_farms=len(farms),
        new_readings=new_readings,
        new_alerts=new_alerts,
    )
