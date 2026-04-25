"""
Analytics route — high-level system stats backed by MySQL.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.db_models import Alert, Farm, FarmReading

router = APIRouter()


@router.get("/farms")
def farm_stats(db: Session = Depends(get_db)):
    farms = db.query(Farm).all()
    out = []
    for f in farms:
        latest = (
            db.query(FarmReading)
            .filter(FarmReading.farm_id == f.id)
            .order_by(FarmReading.fetched_at.desc())
            .first()
        )
        out.append({
            "farm_id": f.id,
            "name": f.name,
            "size_ha": float(f.size_ha),
            "quota_liters": float(f.water_quota_liters),
            "latest_ndvi": None if latest is None or latest.ndvi is None else float(latest.ndvi),
            "latest_soil_moisture_pct": (
                None if latest is None or latest.soil_moisture_pct is None
                else float(latest.soil_moisture_pct)
            ),
            "stress_level": None if latest is None else latest.stress_level,
        })
    return out


@router.get("/system")
def system_stats(db: Session = Depends(get_db)):
    farms = db.query(Farm).all()
    total_quota = sum(float(f.water_quota_liters) for f in farms)
    alert_count = db.query(Alert).count()
    reading_count = db.query(FarmReading).count()
    return {
        "total_farms": len(farms),
        "total_quota_liters": total_quota,
        "alert_count": alert_count,
        "reading_count": reading_count,
    }


@router.get("/fairness")
def fairness(db: Session = Depends(get_db)):
    """
    Simple fairness metric — closer recommended-vs-quota ratios = fairer system.
    Returns 1.0 if there's not enough data.
    """
    farms = db.query(Farm).all()
    ratios = []
    for f in farms:
        if float(f.water_quota_liters) <= 0:
            continue
        latest = (
            db.query(FarmReading)
            .filter(FarmReading.farm_id == f.id)
            .order_by(FarmReading.fetched_at.desc())
            .first()
        )
        if latest is None or latest.recommended_water_liters is None:
            continue
        ratios.append(float(latest.recommended_water_liters) / float(f.water_quota_liters))

    if not ratios:
        return {"fairness_score": 1.0}

    avg = sum(ratios) / len(ratios)
    variance = sum((r - avg) ** 2 for r in ratios) / len(ratios)
    return {"fairness_score": round(max(0.0, 1 - variance), 3)}
