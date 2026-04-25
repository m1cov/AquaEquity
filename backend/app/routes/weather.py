from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.weather.weather_client import fetch_weather

router = APIRouter()


class WeatherTestRequest(BaseModel):
    date: str
    field_geometry: dict[str, Any]


@router.post("/test")
def test_weather(payload: WeatherTestRequest):
    try:
        return fetch_weather(payload.field_geometry, payload.date)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
