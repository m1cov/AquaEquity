"""
Pydantic schemas — the stable API contract between FastAPI and the React frontend.

These shapes match what src/hooks/useFarmData.ts expects. Do not change field
names without also updating the frontend.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class FarmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    region: str
    owner_name: str
    size_ha: float
    latitude: float
    longitude: float
    water_quota_liters: float = 100000
    crop_name: str = "tomato"
    soil_type: str = "loam"


class FarmCreate(FarmBase):
    pass


class FarmRead(FarmBase):
    id: str
    created_at: datetime


class FarmReadingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    farm_id: str
    ndvi: Optional[float] = None
    soil_moisture_pct: Optional[float] = None
    recommended_water_liters: Optional[float] = None
    recommended_window_start: Optional[str] = None
    recommended_window_end: Optional[str] = None
    stress_level: Optional[str] = None
    fetched_at: datetime


class AlertCreate(BaseModel):
    farm_id: Optional[str] = None
    message: str
    severity: str = "info"
    channel: str = "dashboard"
    status: str = "simulated"


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    farm_id: Optional[str] = None
    message: str
    severity: str
    channel: str
    status: str
    created_at: datetime


class IrrigationEventCreate(BaseModel):
    farm_id: str
    water_amount: float = Field(..., gt=0, description="Liters")


class RefreshResponse(BaseModel):
    refreshed_farms: int
    new_readings: int
    new_alerts: int
