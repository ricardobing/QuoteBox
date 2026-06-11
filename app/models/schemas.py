"""Esquemas Pydantic para endpoints y contratos internos."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "0.1.0"


class ScrapeResult(BaseModel):
    status: Literal["success", "error", "partial"] = "success"
    pages_scraped: int = 0
    quotes_found: int = 0
    quotes_new: int = 0
    run_id: str | None = None
    error_detail: str | None = None


class TriggerScrapeRequest(BaseModel):
    reason: str | None = Field(default=None, description="Motivo opcional del disparo manual.")


class WhatsAppWebhookRequest(BaseModel):
    from_phone: str
    body: str


class GenericWebhookResponse(BaseModel):
    ok: bool = True
    detail: str = "accepted"


class ManualIngestWebhookPayload(BaseModel):
    record_id: str
    event_type: str
