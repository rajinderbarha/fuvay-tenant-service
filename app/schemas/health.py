"""Health check response schema."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class ServiceHealth(BaseModel):
    service: str
    status: Literal["ok", "degraded", "down"]
    latency_ms: float | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    version: str
    environment: str
    timestamp: str
    uptime_seconds: float
    services: list[ServiceHealth]
    engines: dict  # from engine_registry.summary()
