"""
Sentinel-2 NDVI & moisture statistics routes.

Credentials come from environment variables only. The backend supports both
naming conventions for compatibility:
  - SENTINEL_CLIENT_ID / SENTINEL_CLIENT_SECRET (used in app/.env)
  - COPERNICUS_CLIENT_ID / COPERNICUS_CLIENT_SECRET (used by data_inputs.py)
"""
from __future__ import annotations

import os

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

load_dotenv()

router = APIRouter(tags=["sentinel"])

TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
)
STATS_URL = "https://sh.dataspace.copernicus.eu/api/v1/statistics"


def _resolve_credentials(client_id: str | None, client_secret: str | None) -> tuple[str, str]:
    cid = (
        client_id
        or os.getenv("SENTINEL_CLIENT_ID")
        or os.getenv("COPERNICUS_CLIENT_ID")
    )
    csec = (
        client_secret
        or os.getenv("SENTINEL_CLIENT_SECRET")
        or os.getenv("COPERNICUS_CLIENT_SECRET")
    )
    if not cid or not csec:
        raise HTTPException(
            status_code=400,
            detail=(
                "Sentinel credentials not configured. Set SENTINEL_CLIENT_ID and "
                "SENTINEL_CLIENT_SECRET (or COPERNICUS_CLIENT_ID/SECRET) in the "
                "backend .env file."
            ),
        )
    return cid, csec


class AuthRequest(BaseModel):
    client_id: str | None = None
    client_secret: str | None = None


class StatisticsRequest(BaseModel):
    access_token: str
    bbox: dict  # {minLon, minLat, maxLon, maxLat}
    date_from: str  # YYYY-MM-DD
    date_to: str  # YYYY-MM-DD


@router.post("/authenticate")
async def authenticate(req: AuthRequest):
    """Get an OAuth2 access token from the Copernicus identity server."""
    client_id, client_secret = _resolve_credentials(req.client_id, req.client_secret)

    try:
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502, detail=f"Authentication request failed: {exc}"
        ) from exc

    if resp.status_code != 200:
        raise HTTPException(
            status_code=401,
            detail="Authentication failed. Check Sentinel client ID and secret.",
        )

    return {"access_token": resp.json()["access_token"]}


@router.post("/statistics")
async def get_statistics(req: StatisticsRequest):
    """
    Compute NDVI and NDMI statistics for a bbox + date range using the
    Sentinel Hub Statistical API.
    """
    evalscript = """//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B04","B08","B8A","B11","dataMask"] }],
    output: [
      { id: "ndvi", bands: 1 },
      { id: "moisture", bands: 1 },
      { id: "dataMask", bands: 1 }
    ]
  };
}
function evaluatePixel(s) {
  let ndvi = (s.B08 - s.B04) / (s.B08 + s.B04 + 1e-6);
  let moisture = (s.B8A - s.B11) / (s.B8A + s.B11 + 1e-6);
  return {
    ndvi: [ndvi],
    moisture: [moisture],
    dataMask: [s.dataMask]
  };
}"""

    body = {
        "input": {
            "bounds": {
                "bbox": [
                    req.bbox["minLon"],
                    req.bbox["minLat"],
                    req.bbox["maxLon"],
                    req.bbox["maxLat"],
                ],
                "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"},
            },
            "data": [
                {"type": "sentinel-2-l2a", "dataFilter": {"mosaickingOrder": "leastCC"}}
            ],
        },
        "aggregation": {
            "timeRange": {
                "from": f"{req.date_from}T00:00:00Z",
                "to": f"{req.date_to}T23:59:59Z",
            },
            "aggregationInterval": {"of": "P1D"},
            "resx": 10,
            "resy": 10,
            "evalscript": evalscript,
        },
        "calculations": {
            "ndvi": {"statistics": {"default": {"percentiles": {"k": [10, 25, 50, 75, 90]}}}},
            "moisture": {"statistics": {"default": {"percentiles": {"k": [10, 25, 50, 75, 90]}}}},
        },
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {req.access_token}",
    }

    try:
        resp = requests.post(STATS_URL, json=body, headers=headers, timeout=120)
    except requests.Timeout as exc:
        raise HTTPException(
            status_code=504,
            detail="Sentinel Hub request timed out. Try a smaller area or shorter date range.",
        ) from exc
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Sentinel Hub request failed: {exc}") from exc

    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Sentinel Hub API error: {resp.text[:500]}",
        )

    return resp.json()
