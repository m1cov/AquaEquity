"""
Extended Kalman Filter (EKF) routes.

These power the Estimator page on the frontend.
"""
from __future__ import annotations

import math
from datetime import date as Date, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.db_models import Farm
from app.services.estimation.crop_parameters import DEFAULT_CROPS, list_crop_parameters
from app.services.estimation.estimator_service import estimator_service
from app.services.estimation.parameters import DEFAULT_SOIL_TYPES, get_crop_params
from app.services.estimation.state_model import relative_available_water, stress_level
from app.services.estimation.water_savings import estimate_water_savings
from app.services.weather.weather_client import fetch_weather, fetch_weather_range

router = APIRouter()


class EstimateRunRequest(BaseModel):
    crop_name: str = "tomato"
    soil_type: str = "loam"
    initial_soil_water_mm: float = 110.0
    date: Optional[str] = None
    field_geometry: Optional[dict[str, Any]] = None
    rain_mm: Optional[float] = None
    et0_mm: Optional[float] = None
    inputs: Optional[dict[str, Any]] = None


class WaterSavingsRequest(BaseModel):
    crop_name: str = "tomato"
    field_area_m2: float
    smart_irrigation_mm_month: float
    baseline_mode: str = "typical"


@router.get("/demo")
def get_ekf_demo(
    days: int = Query(default=10, ge=1, le=60),
    soil_type: str = Query(default="loam"),
):
    """EKF demo for the supported crops — runs a deterministic scenario."""
    try:
        return estimator_service.run_all_crop_demo(days=days, soil_type=soil_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/demo/{crop_name}")
def get_ekf_demo_for_crop(
    crop_name: str,
    days: int = Query(default=10, ge=1, le=60),
    soil_type: str = Query(default="loam"),
):
    try:
        return estimator_service.run_demo_for_crop(crop_name, soil_type=soil_type, days=days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/soil-types/list")
def get_soil_types():
    return {"soil_types": DEFAULT_SOIL_TYPES}


@router.get("/crops/list")
def get_supported_crops():
    return {
        "default_crop_keys": DEFAULT_CROPS,
        "crops": list_crop_parameters(),
    }


def _farm_to_geojson(farm: Farm) -> dict:
    """Build a GeoJSON Polygon from a farm's corner coordinates."""
    has_corners = all(
        v is not None
        for v in [
            farm.top_left_x, farm.top_left_y,
            farm.top_right_x, farm.top_right_y,
            farm.bottom_right_x, farm.bottom_right_y,
            farm.bottom_left_x, farm.bottom_left_y,
        ]
    )
    if has_corners:
        # Corners: X = latitude, Y = longitude; GeoJSON uses [lon, lat]
        coords = [
            [float(farm.top_left_y), float(farm.top_left_x)],
            [float(farm.top_right_y), float(farm.top_right_x)],
            [float(farm.bottom_right_y), float(farm.bottom_right_x)],
            [float(farm.bottom_left_y), float(farm.bottom_left_x)],
        ]
    else:
        lat = float(farm.latitude)
        lon = float(farm.longitude)
        side_m = math.sqrt(float(farm.size_ha) * 10_000) / 2
        d_lat = side_m / 111_320
        d_lon = side_m / (111_320 * math.cos(math.radians(lat)))
        coords = [
            [lon - d_lon, lat + d_lat],
            [lon + d_lon, lat + d_lat],
            [lon + d_lon, lat - d_lat],
            [lon - d_lon, lat - d_lat],
        ]
    coords.append(coords[0])  # close the ring
    return {"type": "Polygon", "coordinates": [coords]}


@router.get("/farm/{farm_id}/live")
def get_farm_live_estimate(
    farm_id: str,
    days: int = Query(default=10, ge=1, le=60),
    db: Session = Depends(get_db),
):
    """
    Run the EKF over the last N calendar days for a farm using real Open-Meteo
    weather and Sentinel-2 satellite data (when Copernicus credentials are set).
    Returns a single scenario shaped identically to the demo endpoint.
    """
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    crop_name = farm.crop_name or "tomato"
    soil_key = (farm.soil_type or "loam").strip().lower().replace(" ", "_")
    if soil_key not in ("loam", "clay_loam"):
        soil_key = "loam"

    try:
        params = get_crop_params(crop_name, soil_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    field_geometry = _farm_to_geojson(farm)

    today = Date.today()
    start = today - timedelta(days=days - 1)
    weather_list = fetch_weather_range(field_geometry, start.isoformat(), today.isoformat())

    ekf = estimator_service.create_filter()
    history = []

    for i, weather in enumerate(weather_list):
        day_str = weather["date"]

        result = estimator_service.run_daily_step(
            ekf=ekf,
            params=params,
            field_geometry=field_geometry,
            date=day_str,
            weather=weather,
        )

        theta = result["x_upd"]
        ndvi_value = result.get("ndvi_mean") or params.default_ndvi

        history.append({
            "day": i + 1,
            "date": day_str,
            "crop": params.crop_name,
            "display_name": params.display_name,
            "soil_type": params.soil_type,
            "rain_mm": round(result["rain_mm"], 2),
            "ndvi": round(float(ndvi_value), 2),
            "et0_mm": round(result["et0_mm"], 2),
            "et0_std_mm": round(result["et0_std_mm"], 2),
            "irrigation_mm": round(result["irrigation_mm"], 2),
            "x_pred_mm": round(result["x_pred"], 2),
            "P_pred": round(result["P_pred"], 2),
            "measurement_mm": (
                None if result["measurement_mm"] is None
                else round(result["measurement_mm"], 2)
            ),
            "moisture_std_mm": (
                None if result.get("moisture_std_mm") is None
                else round(float(result["moisture_std_mm"]), 2)
            ),
            "satellite_available": result["satellite_available"],
            "updated": result["updated"],
            "soil_water_estimate_mm": round(theta, 2),
            "uncertainty": round(result["P_upd"], 2),
            "relative_available_water": round(relative_available_water(theta, params), 3),
            "stress_level": stress_level(theta, params),
            "kalman_gain": (
                None if result["kalman_gain"] is None
                else round(result["kalman_gain"], 3)
            ),
            "innovation": (
                None if result["innovation"] is None
                else round(result["innovation"], 2)
            ),
            "weather_source": result.get("weather_source", "open-meteo"),
        })

    irrigation_trigger_mm = (
        params.theta_fc - params.depletion_fraction_p * (params.theta_fc - params.theta_wp)
    )

    return {
        "farm_id": farm_id,
        "farm_name": farm.name,
        "crop": params.crop_name,
        "display_name": params.display_name,
        "soil_type": params.soil_type,
        "days": days,
        "auto_irrigate": True,
        "parameters": {
            "theta_fc_mm": round(params.theta_fc, 2),
            "theta_wp_mm": round(params.theta_wp, 2),
            "theta_max_mm": round(params.theta_max, 2),
            "irrigation_trigger_mm": round(irrigation_trigger_mm, 2),
            "max_irrigation_mm_day": round(params.max_irrigation_mm_day, 2),
        },
        "crop_parameters": {
            "kc_initial": round(params.kc_initial, 2),
            "kc_mid": round(params.kc_mid, 2),
            "kc_late": round(params.kc_late, 2),
            "depletion_fraction_p": round(params.depletion_fraction_p, 2),
            "root_depth_m": round(params.root_depth_m, 2),
            "default_ndvi": round(params.default_ndvi, 2),
            "notes": params.notes,
            "source_url": params.source_url,
        },
        "history": history,
        "final": history[-1] if history else None,
    }


@router.get("/{farm_id}")
def get_live_estimate(farm_id: str, db: Session = Depends(get_db)):
    """Quick snapshot of the live EKF state for a farm."""
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    return estimator_service.get_live_estimate(farm_id)


@router.post("/run")
def run_real_estimate(payload: EstimateRunRequest):
    try:
        params = get_crop_params(payload.crop_name, payload.soil_type)
        ekf = estimator_service.create_filter(
            initial_soil_water_mm=payload.initial_soil_water_mm
        )

        if payload.inputs is not None:
            return estimator_service.run_daily_step(
                ekf=ekf,
                params=params,
                inputs=payload.inputs,
            )

        if payload.date is None or payload.field_geometry is None:
            raise HTTPException(
                status_code=400,
                detail="Either provide inputs, or provide date and field_geometry.",
            )

        if payload.rain_mm is not None and payload.et0_mm is not None:
            weather = {"rain_mm": payload.rain_mm, "et0_mm": payload.et0_mm}
        else:
            weather = fetch_weather(payload.field_geometry, payload.date)

        return estimator_service.run_daily_step(
            ekf=ekf,
            params=params,
            field_geometry=payload.field_geometry,
            date=payload.date,
            weather=weather,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=400, detail=f"Missing estimator input: {exc.args[0]}"
        ) from exc


@router.post("/water-savings")
def calculate_water_savings(payload: WaterSavingsRequest):
    try:
        return estimate_water_savings(
            crop_name=payload.crop_name,
            field_area_m2=payload.field_area_m2,
            smart_irrigation_mm_month=payload.smart_irrigation_mm_month,
            baseline_mode=payload.baseline_mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
