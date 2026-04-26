from __future__ import annotations

import requests as http_requests
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

JAVA_API_BASE = "https://aqua-equity-api-java-production.up.railway.app"


def _forward(method: str, path: str, body: dict) -> JSONResponse:
    resp = http_requests.request(
        method,
        f"{JAVA_API_BASE}{path}",
        json=body,
        timeout=15,
    )
    try:
        data = resp.json()
    except Exception:
        data = {"detail": resp.text or f"HTTP {resp.status_code}"}

    if not resp.ok and isinstance(data, dict):
        # Normalize Java error shape → FastAPI detail shape for consistent frontend parsing
        msg = data.get("message") or data.get("error") or f"HTTP {resp.status_code}"
        data = {"detail": msg}

    return JSONResponse(content=data, status_code=resp.status_code)


@router.post("/login")
async def proxy_login(request: Request):
    body = await request.json()
    return _forward("POST", "/api/auth/login", body)


@router.post("/register")
async def proxy_register(request: Request):
    body = await request.json()
    return _forward("POST", "/api/users", body)
