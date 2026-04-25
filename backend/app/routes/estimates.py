"""
Extended Kalman Filter (EKF) routes.

These power the Estimator page on the frontend.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.db_models import Farm
from app.services.estimation.crop_parameters import DEFAULT_CROPS, list_crop_parameters
from app.services.estimation.estimator_service import estimator_service
from app.services.estimation.parameters import DEFAULT_SOIL_TYPES, get_crop_params
from app.services.estimation.water_savings import estimate_water_savings
from app.services.weather.weather_client import fetch_weather

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
