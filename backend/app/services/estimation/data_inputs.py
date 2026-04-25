from __future__ import annotations

import json
import os
import time
from datetime import date as Date
from datetime import timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


STATISTICS_URL = "https://sh.dataspace.copernicus.eu/api/v1/statistics"
TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

NDMI_MIN = -0.2
NDMI_MAX = 0.6
MIN_SATELLITE_R_VARIANCE = 4.0
REQUEST_TIMEOUT_SECONDS = 30

_TOKEN_CACHE: dict[str, Any] = {
    "access_token": None,
    "expires_at": 0.0,
}


SENTINEL2_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{
      bands: ["B04", "B08", "B8A", "B11", "SCL", "dataMask"]
    }],
    output: [
      { id: "indices", bands: ["ndvi", "ndmi"], sampleType: "FLOAT32" },
      { id: "dataMask", bands: 1 }
    ]
  };
}

function isClearPixel(sample) {
  // Exclude no-data, saturated, cloud shadow, clouds, cirrus, and snow/ice.
  const badScl = [0, 1, 3, 8, 9, 10, 11];
  return sample.dataMask === 1 && badScl.indexOf(sample.SCL) === -1;
}

function safeIndex(a, b) {
  const denominator = a + b;
  if (Math.abs(denominator) < 0.000001) {
    return 0;
  }
  return (a - b) / denominator;
}

function evaluatePixel(sample) {
  const valid = isClearPixel(sample) ? 1 : 0;
  return {
    indices: [
      safeIndex(sample.B08, sample.B04),
      safeIndex(sample.B8A, sample.B11)
    ],
    dataMask: [valid]
  };
}
"""


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def moisture_index_to_mm(ndmi: float | None, params: Any) -> float | None:
    """
    Convert Sentinel-2 NDMI into the EKF soil-water state units [mm].

    This is an MVP linear calibration from NDMI into the current model's
    wilting-point to field-capacity storage range.
    """
    if ndmi is None or params is None:
        return None

    alpha = (float(ndmi) - NDMI_MIN) / (NDMI_MAX - NDMI_MIN)
    alpha = _clamp(alpha, 0.0, 1.0)
    return float(params.theta_wp) + alpha * (float(params.theta_fc) - float(params.theta_wp))


def moisture_index_std_to_mm(moisture_std_index: float | None, params: Any) -> float | None:
    """Convert NDMI standard deviation into EKF soil-water state units [mm]."""
    if moisture_std_index is None or params is None:
        return None

    scale = (float(params.theta_fc) - float(params.theta_wp)) / (NDMI_MAX - NDMI_MIN)
    return abs(float(moisture_std_index)) * scale


def _weather_inputs(weather: dict | None) -> dict:
    if weather is None:
        raise ValueError("Weather input is required and must include rain_mm and et0_mm.")

    if "rain_mm" not in weather or "et0_mm" not in weather:
        raise ValueError("Weather input must include rain_mm and et0_mm.")

    rain_mm = float(weather["rain_mm"])
    et0_mm = float(weather["et0_mm"])

    if "rain_std_mm" in weather:
        rain_std_mm = float(weather["rain_std_mm"])
    elif rain_mm <= 0.1:
        rain_std_mm = 0.2
    else:
        rain_std_mm = max(1.0, 0.40 * rain_mm)

    if "et0_std_mm" in weather:
        et0_std_mm = float(weather["et0_std_mm"])
    else:
        et0_std_mm = max(0.5, 0.20 * et0_mm)

    return {
        "rain_mm": rain_mm,
        "rain_std_mm": rain_std_mm,
        "et0_mm": et0_mm,
        "et0_std_mm": et0_std_mm,
        "Q_weather": rain_std_mm**2 + et0_std_mm**2,
        "weather_source": weather.get("weather_source", "provided"),
    }


def _empty_inputs(weather: dict) -> dict:
    return {
        "satellite_available": False,
        "ndvi_mean": None,
        "ndvi_std": None,
        "moisture_mean_mm": None,
        "moisture_std_mm": None,
        "valid_pixel_count": 0,
        "R_satellite": None,
        **weather,
    }


def _date_range_for_day(value: str) -> tuple[str, str]:
    day = Date.fromisoformat(value[:10])
    next_day = day + timedelta(days=1)
    return f"{day.isoformat()}T00:00:00Z", f"{next_day.isoformat()}T00:00:00Z"


def _geometry_from_field(field_geometry: dict) -> dict:
    if field_geometry.get("type") == "Feature" and isinstance(field_geometry.get("geometry"), dict):
        return field_geometry["geometry"]
    return field_geometry


def _get_access_token() -> str | None:
    # Support both naming conventions for the Copernicus credentials.
    client_id = os.getenv("SENTINEL_CLIENT_ID") or os.getenv("COPERNICUS_CLIENT_ID")
    client_secret = (
        os.getenv("SENTINEL_CLIENT_SECRET") or os.getenv("COPERNICUS_CLIENT_SECRET")
    )
    if not client_id or not client_secret:
        return None

    now = time.time()
    cached_token = _TOKEN_CACHE.get("access_token")
    if cached_token and now < float(_TOKEN_CACHE.get("expires_at", 0.0)):
        return str(cached_token)

    body = urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }).encode("utf-8")
    request = Request(
        TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))

    access_token = payload.get("access_token")
    if not access_token:
        return None

    expires_in = int(payload.get("expires_in", 3600))
    _TOKEN_CACHE["access_token"] = access_token
    _TOKEN_CACHE["expires_at"] = now + max(expires_in - 60, 60)
    return str(access_token)


def _statistics_payload(field_geometry: dict, date: str) -> dict:
    date_from, date_to = _date_range_for_day(date)
    return {
        "input": {
            "bounds": {
                "geometry": _geometry_from_field(field_geometry),
                "properties": {
                    "crs": "http://www.opengis.net/def/crs/EPSG/0/4326",
                },
            },
            "data": [
                {
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "timeRange": {
                            "from": date_from,
                            "to": date_to,
                        },
                        "mosaickingOrder": "leastCC",
                    },
                },
            ],
        },
        "aggregation": {
            "timeRange": {
                "from": date_from,
                "to": date_to,
            },
            "aggregationInterval": {
                "of": "P1D",
            },
            "evalscript": SENTINEL2_EVALSCRIPT,
            "resx": 10,
            "resy": 10,
        },
    }


def _post_statistics(payload: dict, token: str) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        STATISTICS_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def _read_band_stats(response: dict, band_name: str) -> dict | None:
    intervals = response.get("data") or []
    if not intervals:
        return None

    outputs = intervals[0].get("outputs") or {}
    indices_output = outputs.get("indices") or outputs.get("default") or {}
    bands = indices_output.get("bands") or {}
    band = bands.get(band_name) or {}
    stats = band.get("stats")
    if not stats:
        return None

    sample_count = int(stats.get("sampleCount") or 0)
    no_data_count = int(stats.get("noDataCount") or 0)
    valid_pixel_count = max(sample_count - no_data_count, 0)

    return {
        "mean": stats.get("mean"),
        "std": stats.get("stDev"),
        "valid_pixel_count": valid_pixel_count,
    }


def _satellite_inputs(field_geometry: dict, date: str, params: Any) -> dict | None:
    token = _get_access_token()
    if not token:
        return None

    response = _post_statistics(_statistics_payload(field_geometry, date), token)
    ndvi_stats = _read_band_stats(response, "ndvi")
    ndmi_stats = _read_band_stats(response, "ndmi")
    if not ndvi_stats or not ndmi_stats:
        return None

    valid_pixel_count = min(
        int(ndvi_stats["valid_pixel_count"]),
        int(ndmi_stats["valid_pixel_count"]),
    )
    if valid_pixel_count <= 0:
        return None

    ndvi_mean = ndvi_stats["mean"]
    ndmi_mean = ndmi_stats["mean"]
    if ndvi_mean is None or ndmi_mean is None:
        return None

    moisture_mean_mm = moisture_index_to_mm(float(ndmi_mean), params)
    moisture_std_mm = moisture_index_std_to_mm(ndmi_stats["std"], params)
    r_satellite = None
    if moisture_std_mm is not None:
        r_satellite = max(moisture_std_mm**2, MIN_SATELLITE_R_VARIANCE)

    return {
        "satellite_available": True,
        "ndvi_mean": float(ndvi_mean),
        "ndvi_std": None if ndvi_stats["std"] is None else float(ndvi_stats["std"]),
        "moisture_mean_mm": moisture_mean_mm,
        "moisture_std_mm": moisture_std_mm,
        "valid_pixel_count": valid_pixel_count,
        "R_satellite": r_satellite,
    }


def get_estimator_inputs(
    field_geometry: dict | None,
    date: str,
    weather: dict | None = None,
    params: Any = None,
) -> dict:
    """
    Build one EKF-ready input packet from weather and Sentinel-2 statistics.

    Weather values are in mm/day. Satellite NDMI is converted into the model's
    root-zone storage units [mm] when crop/soil params are provided.
    """
    weather_values = _weather_inputs(weather)
    inputs = _empty_inputs(weather_values)

    if not field_geometry:
        return inputs

    try:
        satellite_values = _satellite_inputs(field_geometry, date, params)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError, json.JSONDecodeError):
        satellite_values = None

    if satellite_values is not None:
        inputs.update(satellite_values)

    return inputs
