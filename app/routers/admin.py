"""Router para operaciones del panel admin."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.database import get_supabase_client
from app.services.quotes import upsert_quote_manual

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin")


class QuoteManualCreate(BaseModel):
    text: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)
    source: str = "manual"


@router.post("/quotes/manual", status_code=201)
def create_quote_manual(payload: QuoteManualCreate) -> dict[str, Any]:
    if not payload.text.strip() or not payload.author.strip():
        raise HTTPException(status_code=422, detail="text y author son obligatorios.")

    from app.config import get_settings

    settings = get_settings()
    supabase = get_supabase_client(settings)

    from app.scraper.ingestor import compute_text_hash, normalize_text_for_hash

    normalized = normalize_text_for_hash(payload.text)
    text_hash = compute_text_hash(normalized)

    existing = (
        supabase.table("quotes")
        .select("id")
        .eq("text_hash", text_hash)
        .limit(1)
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=409, detail="Esta frase ya existe en el storage.")

    result = upsert_quote_manual(supabase, payload.text, payload.author, payload.tags)
    if not result:
        raise HTTPException(status_code=409, detail="Esta frase ya existe en el storage.")

    return {"ok": True, "detail": f"Frase de {payload.author} cargada.", "quote": result}


@router.delete("/quotes/{quote_id}")
def delete_quote(quote_id: str) -> dict[str, Any]:
    from app.config import get_settings

    settings = get_settings()
    supabase = get_supabase_client(settings)

    existing = supabase.table("quotes").select("id").eq("id", quote_id).limit(1).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Quote no encontrada.")

    supabase.table("quotes").delete().eq("id", quote_id).execute()
    return {"deleted": True}
