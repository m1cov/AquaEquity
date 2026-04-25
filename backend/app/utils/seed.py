"""
Seed initial demo farms.

Idempotent: if any farms already exist, this is a no-op. Once the user's
real schema is in place, they can either remove this file or replace the
seed data with their own.
"""
from __future__ import annotations

from app.db import SessionLocal
from app.db_models import Farm

# Skopje-area demo farms. Coordinates are reasonable for North Macedonia.
SEED_FARMS = [
    {
        "name": "Stojanov South",
        "region": "Skopje",
        "owner_name": "Petar Stojanov",
        "size_ha": 12.5,
        "latitude": 41.9981,
        "longitude": 21.4254,
        "water_quota_liters": 500_000,
        "crop_name": "tomato",
        "soil_type": "loam",
    },
    {
        "name": "Stojanov East",
        "region": "Skopje",
        "owner_name": "Petar Stojanov",
        "size_ha": 8.0,
        "latitude": 41.9900,
        "longitude": 21.4500,
        "water_quota_liters": 320_000,
        "crop_name": "maize",
        "soil_type": "loam",
    },
    {
        "name": "Tikvesh Vines",
        "region": "Tikvesh",
        "owner_name": "Petar Stojanov",
        "size_ha": 6.4,
        "latitude": 41.5500,
        "longitude": 22.0200,
        "water_quota_liters": 200_000,
        "crop_name": "wheat",
        "soil_type": "clay_loam",
    },
    {
        "name": "Pelagonia North",
        "region": "Pelagonia",
        "owner_name": "Petar Stojanov",
        "size_ha": 18.2,
        "latitude": 41.0314,
        "longitude": 21.3343,
        "water_quota_liters": 720_000,
        "crop_name": "wheat",
        "soil_type": "loam",
    },
    {
        "name": "Polog West",
        "region": "Polog",
        "owner_name": "Petar Stojanov",
        "size_ha": 4.5,
        "latitude": 41.9986,
        "longitude": 20.9714,
        "water_quota_liters": 180_000,
        "crop_name": "tomato",
        "soil_type": "loam",
    },
]


def seed_initial_farms() -> None:
    db = SessionLocal()
    try:
        existing = db.query(Farm).count()
        if existing > 0:
            return
        for f in SEED_FARMS:
            db.add(Farm(**f))
        db.commit()
    finally:
        db.close()
