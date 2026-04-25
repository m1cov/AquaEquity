"""
AquaField API — FastAPI entry point.

Run from the `backend/` directory:
    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.routes import alerts, analytics, estimates, farms, irrigation, sentinel, weather
from app.utils.seed import seed_initial_farms

load_dotenv()

app = FastAPI(title="AquaField API", version="0.2.0")

# CORS — allow local Vite dev server and production frontend (configurable)
default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
extra = os.getenv("CORS_ORIGINS", "")
origins = default_origins + [o.strip() for o in extra.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    seed_initial_farms()


@app.get("/")
def root():
    return {"message": "AquaField API running"}


@app.get("/health")
def health():
    return {"status": "ok"}


# Routers
app.include_router(farms.router, prefix="/farms", tags=["Farms"])
app.include_router(irrigation.router, prefix="/irrigate", tags=["Irrigation"])
app.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(sentinel.router, prefix="/sentinel", tags=["Sentinel"])
app.include_router(estimates.router, prefix="/estimates", tags=["EKF Estimates"])
app.include_router(weather.router, prefix="/weather", tags=["Weather"])
