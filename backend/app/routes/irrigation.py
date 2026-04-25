"""
Irrigation route — records water usage events against farm quotas.

Endpoints:
- POST /irrigate/        log an irrigation event for a farm
- GET  /irrigate/usage   per-farm usage summary
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.db_models import Farm, FarmReading
from app.schemas import IrrigationEventCreate

router = APIRouter()


@router.post("/")
def log_irrigation(event: IrrigationEventCreate, db: Session = Depends(get_db)):
    """
    Log an irrigation event.

    For now we only validate against quota and return the remaining budget.
    Persistence of irrigation events themselves can be added when the user's
    schema includes that table — the recommended_water_liters field on
    FarmReading already covers the planned-volume case.
    """
    farm = db.query(Farm).filter(Farm.id == event.farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    used_today = _used_today(db, farm.id)
    if used_today + event.water_amount > float(farm.water_quota_liters):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Quota exceeded. Used {used_today:.0f} L of "
                f"{float(farm.water_quota_liters):.0f} L today."
            ),
        )

    return {
        "message": "Irrigation recorded",
        "farm_id": farm.id,
        "water_amount": event.water_amount,
        "used_today": used_today + event.water_amount,
        "remaining_quota": float(farm.water_quota_liters) - used_today - event.water_amount,
    }


@router.get("/usage")
def usage_summary(db: Session = Depends(get_db)):
    farms = db.query(Farm).all()
    return [
        {
            "farm_id": f.id,
            "name": f.name,
            "quota_liters": float(f.water_quota_liters),
            "used_today_liters": _used_today(db, f.id),
        }
        for f in farms
    ]


def _used_today(db: Session, farm_id: str) -> float:
    """
    Approximate "used today" from the most recent recommended_water_liters in
    the past 24h. When a real irrigation_events table arrives we replace this
    with a SUM over that table.
    """
    since = datetime.utcnow() - timedelta(days=1)
    readings = (
        db.query(FarmReading)
        .filter(
            FarmReading.farm_id == farm_id,
            FarmReading.fetched_at >= since,
        )
        .all()
    )
    return float(
        sum((r.recommended_water_liters or 0) for r in readings)
    )
