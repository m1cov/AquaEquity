from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS = 20


def _weather_uncertainty(rain_mm: float, et0_mm: float) -> dict:
    rain_std_mm = 0.2 if rain_mm <= 0.1 else max(1.0, 0.40 * rain_mm)
    et0_std_mm = max(0.5, 0.20 * et0_mm)

    return {
        "rain_std_mm": rain_std_mm,
        "et0_std_mm": et0_std_mm,
        "Q_weather": rain_std_mm**2 + et0_std_mm**2,
    }


def _fallback_weather() -> dict:
    rain_mm = 0.0
    et0_mm = 5.0

    return {
        "rain_mm": rain_mm,
        "et0_mm": et0_mm,
        **_weather_uncertainty(rain_mm, et0_mm),
        "weather_source": "fallback",
    }


def _geometry_from_field(field_geometry: dict[str, Any]) -> dict[str, Any]:
    if field_geometry.get("type") == "Feature" and isinstance(field_geometry.get("geometry"), dict):
        return field_geometry["geometry"]
    return field_geometry


def _polygon_centroid(field_geometry: dict[str, Any]) -> tuple[float, float]:
    """
    Return a representative (latitude, longitude) for a GeoJSON polygon.

    GeoJSON coordinates are [longitude, latitude]. For the MVP, we average the
    outer ring vertices and ignore a repeated closing point when present.
    """
    geometry = _geometry_from_field(field_geometry)
    if geometry.get("type") != "Polygon":
        raise ValueError("field_geometry must be a GeoJSON Polygon or Feature containing a Polygon.")

    rings = geometry.get("coordinates")
    if not rings or not isinstance(rings, list) or not rings[0]:
        raise ValueError("field_geometry Polygon has no coordinates.")

    vertices = list(rings[0])
    if len(vertices) > 1 and vertices[0] == vertices[-1]:
        vertices = vertices[:-1]

    if not vertices:
        raise ValueError("field_geometry Polygon has no vertices.")

    lon_sum = 0.0
    lat_sum = 0.0
    for vertex in vertices:
        lon_sum += float(vertex[0])
        lat_sum += float(vertex[1])

    count = float(len(vertices))
    return lat_sum / count, lon_sum / count


def _open_meteo_url(latitude: float, longitude: float, date: str) -> str:
    day = date[:10]
    query = urlencode({
        "latitude": latitude,
        "longitude": longitude,
        "daily": "precipitation_sum,et0_fao_evapotranspiration",
        "start_date": day,
        "end_date": day,
        "timezone": "auto",
    })
    return f"{OPEN_METEO_FORECAST_URL}?{query}"


def _fetch_open_meteo(latitude: float, longitude: float, date: str) -> dict:
    request = Request(
        _open_meteo_url(latitude, longitude, date),
        headers={"Accept": "application/json"},
        method="GET",
    )

    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def _parse_open_meteo_weather(payload: dict) -> dict:
    daily = payload.get("daily") or {}
    rain_values = daily.get("precipitation_sum") or []
    et0_values = daily.get("et0_fao_evapotranspiration") or []

    if not rain_values or not et0_values or rain_values[0] is None or et0_values[0] is None:
        raise ValueError("Open-Meteo response is missing precipitation or ET0 values.")

    rain_mm = float(rain_values[0])
    et0_mm = float(et0_values[0])

    return {
        "rain_mm": rain_mm,
        "et0_mm": et0_mm,
        **_weather_uncertainty(rain_mm, et0_mm),
        "weather_source": "open-meteo",
    }


def fetch_weather(field_geometry: dict[str, Any], date: str) -> dict:
    """
    Fetch daily weather inputs for the estimator.

    Returns rain and ET0 in mm/day. API failures fall back to conservative MVP
    defaults so the EKF prediction can still run.
    """
    try:
        latitude, longitude = _polygon_centroid(field_geometry)
        payload = _fetch_open_meteo(latitude, longitude, date)
        return _parse_open_meteo_weather(payload)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError, json.JSONDecodeError):
        return _fallback_weather()


def fetch_weather_range(
    field_geometry: dict[str, Any],
    start_date: str,
    end_date: str,
) -> list[dict]:
    """
    Fetch daily weather for a date range in a single Open-Meteo request.
    Returns a list ordered oldest-to-newest, one dict per day including a 'date' key.
    Falls back to conservative defaults per day when the API call fails.
    """
    from datetime import date as _Date, timedelta

    def _fallback_range() -> list[dict]:
        s = _Date.fromisoformat(start_date[:10])
        e = _Date.fromisoformat(end_date[:10])
        n = max((e - s).days + 1, 1)
        return [
            {"date": (s + timedelta(days=i)).isoformat(), **_fallback_weather()}
            for i in range(n)
        ]

    try:
        latitude, longitude = _polygon_centroid(field_geometry)
        query = urlencode({
            "latitude": latitude,
            "longitude": longitude,
            "daily": "precipitation_sum,et0_fao_evapotranspiration",
            "start_date": start_date[:10],
            "end_date": end_date[:10],
            "timezone": "auto",
        })
        request = Request(
            f"{OPEN_METEO_FORECAST_URL}?{query}",
            headers={"Accept": "application/json"},
            method="GET",
        )
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))

        daily = payload.get("daily") or {}
        dates = daily.get("time") or []
        rain_list = daily.get("precipitation_sum") or []
        et0_list = daily.get("et0_fao_evapotranspiration") or []

        result = []
        for i, day_str in enumerate(dates):
            rain_mm = float(rain_list[i]) if i < len(rain_list) and rain_list[i] is not None else 0.0
            et0_mm = float(et0_list[i]) if i < len(et0_list) and et0_list[i] is not None else 5.0
            result.append({
                "date": day_str,
                "rain_mm": rain_mm,
                "et0_mm": et0_mm,
                **_weather_uncertainty(rain_mm, et0_mm),
                "weather_source": "open-meteo",
            })
        return result if result else _fallback_range()
    except (HTTPError, URLError, TimeoutError, ValueError, OSError, json.JSONDecodeError):
        return _fallback_range()
