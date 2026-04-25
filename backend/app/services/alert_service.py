"""
Alert service.

Given a farm and its latest reading, decide whether an alert should be
generated. Uses the same NDVI/soil-moisture thresholds the frontend renders
against (lib/irrigation.ts).
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.db_models import Alert, Farm, FarmReading
from app.utils.sms_notifier import send_sms


def evaluate_and_create_alerts(
    db: Session,
    farm: Farm,
    reading: Optional[FarmReading],
) -> list[Alert]:
    """
    Returns the list of newly-created Alert ORM objects (already added to the
    session, not yet committed).
    """
    if reading is None:
        return []

    new_alerts: list[Alert] = []

    # Stressed crop -> warning
    if reading.stress_level == "stressed":
        msg = (
            f"{farm.name} is stressed. Consider irrigating "
            f"{int(float(reading.recommended_water_liters or 0)):,} L "
            f"between {reading.recommended_window_start} and {reading.recommended_window_end}."
        )
        alert = Alert(
            farm_id=farm.id,
            message=msg,
            severity="warning",
            channel="dashboard",
            status="simulated",
        )
        db.add(alert)
        send_sms(msg)
        new_alerts.append(alert)

    # Very low soil moisture -> critical
    if reading.soil_moisture_pct is not None and float(reading.soil_moisture_pct) < 15:
        msg = (
            f"Critical soil moisture at {farm.name}: "
            f"{float(reading.soil_moisture_pct):.0f}%."
        )
        alert = Alert(
            farm_id=farm.id,
            message=msg,
            severity="critical",
            channel="dashboard",
            status="simulated",
        )
        db.add(alert)
        send_sms(msg)
        new_alerts.append(alert)

    return new_alerts
