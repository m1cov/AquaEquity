from __future__ import annotations

import math

from app.db import SessionLocal
from app.db_models import Farm


def _corners(lat: float, lon: float, size_ha: float) -> dict:
    """Compute axis-aligned bounding box corners from center + area."""
    side_m = math.sqrt(size_ha * 10000) / 2
    d_lat = side_m / 111320
    d_lon = side_m / (111320 * math.cos(math.radians(lat)))
    return {
        "top_left_x": round(lat + d_lat, 6),
        "top_left_y": round(lon - d_lon, 6),
        "top_right_x": round(lat + d_lat, 6),
        "top_right_y": round(lon + d_lon, 6),
        "bottom_left_x": round(lat - d_lat, 6),
        "bottom_left_y": round(lon - d_lon, 6),
        "bottom_right_x": round(lat - d_lat, 6),
        "bottom_right_y": round(lon + d_lon, 6),
    }


_BASE_FARMS = [
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

SEED_FARMS = [
    {**f, **_corners(f["latitude"], f["longitude"], f["size_ha"])}
    for f in _BASE_FARMS
]


def seed_initial_farms() -> None:
    db = SessionLocal()
    try:
        existing = db.query(Farm).count()
        if existing > 0:
            # Patch existing farms that are missing corner data
            for farm in db.query(Farm).all():
                if farm.top_left_x is None:
                    corners = _corners(farm.latitude, farm.longitude, float(farm.size_ha))
                    for k, v in corners.items():
                        setattr(farm, k, v)
            db.commit()
            return
        for f in SEED_FARMS:
            db.add(Farm(**f))
        db.commit()
    finally:
        db.close()
