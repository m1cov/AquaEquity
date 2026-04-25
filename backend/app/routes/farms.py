"""
Farms route — DB-backed.

Endpoints exposed to the frontend:
- GET    /farms/                    list all farms
- POST   /farms/                    create a farm
- GET    /farms/readings/all        all readings, newest first (used by dashboard)
- POST   /farms/refresh             run a refresh cycle and persist a new
                                    FarmReading per farm (replaces Supabase
                                    `refresh-farm-data` edge function)
- GET    /farms/{farm_id}           single farm
- GET    /farms/{farm_id}/readings  reading history for a farm
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.db_models import Farm, FarmReading
from app.schemas import FarmCreate, FarmRead, FarmReadingRead, RefreshResponse
from app.services.refresh_service import refresh_all_farms

router = APIRouter()


@router.get("/", response_model=List[FarmRead])
def list_farms(db: Session = Depends(get_db)):
    return db.query(Farm).order_by(Farm.name).all()


@router.post("/", response_model=FarmRead, status_code=201)
def create_farm(payload: FarmCreate, db: Session = Depends(get_db)):
    farm = Farm(**payload.model_dump())
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


@router.get("/readings/all", response_model=List[FarmReadingRead])
def list_all_readings(limit: int = 500, db: Session = Depends(get_db)):
    """All readings ordered by fetched_at desc. Frontend filters by farm_id client-side."""
    return (
        db.query(FarmReading)
        .order_by(FarmReading.fetched_at.desc())
        .limit(limit)
        .all()
    )


@router.post("/refresh", response_model=RefreshResponse)
def refresh_readings(db: Session = Depends(get_db)):
    """Run a refresh cycle. Replaces Supabase's `refresh-farm-data` edge function."""
    return refresh_all_farms(db)


@router.get("/{farm_id}", response_model=FarmRead)
def get_farm(farm_id: str, db: Session = Depends(get_db)):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    return farm


@router.get("/{farm_id}/readings", response_model=List[FarmReadingRead])
def get_farm_readings(farm_id: str, limit: int = 100, db: Session = Depends(get_db)):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    return (
        db.query(FarmReading)
        .filter(FarmReading.farm_id == farm_id)
        .order_by(FarmReading.fetched_at.desc())
        .limit(limit)
        .all()
    )
