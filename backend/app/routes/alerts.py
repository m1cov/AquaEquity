"""
Alerts route — DB-backed.

Endpoints:
- GET  /alerts/         list alerts (most recent first)
- POST /alerts/send     create an alert (replaces Supabase `send-sms` function)
- POST /alerts/trigger  re-evaluate every farm and create alerts where needed
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.db_models import Alert, Farm, FarmReading
from app.schemas import AlertCreate, AlertRead
from app.services.alert_service import evaluate_and_create_alerts

router = APIRouter()


@router.get("/", response_model=List[AlertRead])
def list_alerts(limit: int = 100, db: Session = Depends(get_db)):
    return (
        db.query(Alert)
        .order_by(Alert.created_at.desc())
        .limit(limit)
        .all()
    )


@router.post("/send", response_model=AlertRead, status_code=201)
def send_alert(payload: AlertCreate, db: Session = Depends(get_db)):
    """Create an alert (used by the 'Send test alert' button on the frontend)."""
    alert = Alert(**payload.model_dump())
    db.add(alert)
    db.commit()
    db.refresh(alert)
    # Future hook: call SMS provider here when payload.channel == "sms"
    return alert


@router.post("/trigger", response_model=List[AlertRead])
def trigger_alerts(db: Session = Depends(get_db)):
    """
    Re-evaluate every farm using its latest reading and create alerts
    for stressed farms / low-quota cases.
    """
    farms = db.query(Farm).all()
    new_alerts = []
    for farm in farms:
        latest_reading = (
            db.query(FarmReading)
            .filter(FarmReading.farm_id == farm.id)
            .order_by(FarmReading.fetched_at.desc())
            .first()
        )
        new_alerts.extend(evaluate_and_create_alerts(db, farm, latest_reading))
    db.commit()
    return new_alerts
