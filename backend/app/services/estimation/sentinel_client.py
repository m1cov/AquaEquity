# app/services/sentinel_client.py

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()


SENTINEL_TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/"
    "protocol/openid-connect/token"
)

SENTINEL_STATS_URL = "https://sh.dataspace.copernicus.eu/api/v1/statistics"


@dataclass
class SentinelMeasurement:
    day_index: int
    date: str

    ndvi_mean: float | None
    ndvi_std: float | None

    moisture_mean: float | None
    moisture_std: float | None

    soil_water_mm: float | None


def get_sentinel_access_token() -> str:
    client_id = os.getenv("SENTINEL_CLIENT_ID")
    client_secret = os.getenv("SENTINEL_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError(
            "Missing Sentinel credentials. Set SENTINEL_CLIENT_ID and "
            "SENTINEL_CLIENT_SECRET in your .env file."
        )

    response = requests.post(
        SENTINEL_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=20,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Sentinel authentication failed: {response.status_code} {response.text}"
        )

    return response.json()["access_token"]


def fetch_sentinel_statistics(
    *,
    bbox: dict,
    date_from: str,
    date_to: str,
    access_token: str,
) -> dict:
    """
    Fetch NDVI and moisture statistics from Sentinel-2 L2A.

    bbox format:
    {
        "minLon": 21.30,
        "minLat": 41.95,
        "maxLon": 21.32,
        "maxLat": 41.97,
    }
    """

    evalscript = """
//VERSION=3

function setup() {
  return {
    input: [{
      bands: ["B04", "B08", "B8A", "B11", "SCL", "dataMask"]
    }],
    output: [
      { id: "ndvi", bands: 1, sampleType: "FLOAT32" },
      { id: "moisture", bands: 1, sampleType: "FLOAT32" },
      { id: "dataMask", bands: 1 }
    ]
  };
}

function isValidPixel(s) {
  // Sentinel-2 Scene Classification Layer:
  // 3 = cloud shadow
  // 8 = medium probability cloud
  // 9 = high probability cloud
  // 10 = thin cirrus
  // 11 = snow / ice
  if (s.dataMask === 0) return 0;
  if ([3, 8, 9, 10, 11].includes(s.SCL)) return 0;
  return 1;
}

function evaluatePixel(s) {
  let valid = isValidPixel(s);

  let ndvi = (s.B08 - s.B04) / (s.B08 + s.B04 + 1e-6);
  let moisture = (s.B8A - s.B11) / (s.B8A + s.B11 + 1e-6);

  return {
    ndvi: [ndvi],
    moisture: [moisture],
    dataMask: [valid]
  };
}
"""

    body = {
        "input": {
            "bounds": {
                "bbox": [
                    bbox["minLon"],
                    bbox["minLat"],
                    bbox["maxLon"],
                    bbox["maxLat"],
                ],
                "properties": {
                    "crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
                },
            },
            "data": [
                {
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "mosaickingOrder": "leastCC"
                    },
                }
            ],
        },
        "aggregation": {
            "timeRange": {
                "from": f"{date_from}T00:00:00Z",
                "to": f"{date_to}T23:59:59Z",
            },
            "aggregationInterval": {
                "of": "P1D"
            },
            "resx": 10,
            "resy": 10,
            "evalscript": evalscript,
        },
        "calculations": {
            "ndvi": {
                "statistics": {
                    "default": {
                        "percentiles": {
                            "k": [10, 25, 50, 75, 90]
                        }
                    }
                }
            },
            "moisture": {
                "statistics": {
                    "default": {
                        "percentiles": {
                            "k": [10, 25, 50, 75, 90]
                        }
                    }
                }
            },
        },
    }

    response = requests.post(
        SENTINEL_STATS_URL,
        json=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        timeout=120,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Sentinel statistics request failed: "
            f"{response.status_code} {response.text}"
        )

    return response.json()