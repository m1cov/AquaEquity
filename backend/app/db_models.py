"""
SQLAlchemy ORM models.

Field names match the React frontend's expectations from src/hooks/useFarmData.ts:
- Farm: id, name, region, owner_name, size_ha, latitude, longitude, water_quota_liters
- FarmReading: id, farm_id, ndvi, soil_moisture_pct, recommended_water_liters,
               recommended_window_start, recommended_window_end, stress_level, fetched_at
- Alert: id, farm_id, message, severity, channel, status, created_at

NOTE: Once the user provides their own MySQL schema, swap these models to
match. The Pydantic schemas in app/schemas.py act as the API contract and
should remain stable — only this file needs to change.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Farm(Base):
    __tablename__ = "farms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    region: Mapped[str] = mapped_column(String(120), nullable=False)
    owner_name: Mapped[str] = mapped_column(String(120), nullable=False)
    size_ha: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    water_quota_liters: Mapped[float] = mapped_column(
        Numeric(14, 2), nullable=False, default=100000
    )
    crop_name: Mapped[str] = mapped_column(String(40), nullable=False, default="tomato")
    soil_type: Mapped[str] = mapped_column(String(40), nullable=False, default="loam")
    top_left_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    top_left_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    top_right_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    top_right_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    bottom_left_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    bottom_left_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    bottom_right_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    bottom_right_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    readings: Mapped[list["FarmReading"]] = relationship(
        "FarmReading",
        back_populates="farm",
        cascade="all, delete-orphan",
        order_by="FarmReading.fetched_at.desc()",
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert",
        back_populates="farm",
        cascade="all, delete-orphan",
    )


class FarmReading(Base):
    __tablename__ = "farm_readings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    farm_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ndvi: Mapped[float | None] = mapped_column(Numeric(5, 3), nullable=True)
    soil_moisture_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    recommended_water_liters: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    recommended_window_start: Mapped[str | None] = mapped_column(String(8), nullable=True)
    recommended_window_end: Mapped[str | None] = mapped_column(String(8), nullable=True)
    stress_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    farm: Mapped["Farm"] = relationship("Farm", back_populates="readings")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    farm_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("farms.id", ondelete="CASCADE"), nullable=True, index=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="info")
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="dashboard")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="simulated")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    farm: Mapped["Farm | None"] = relationship("Farm", back_populates="alerts")
