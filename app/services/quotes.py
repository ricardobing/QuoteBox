"""Operaciones de consulta y actualización sobre frases."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from supabase import Client

from app.scraper.ingestor import compute_text_hash, normalize_author, normalize_text_for_hash


def count_quotes_by_author(supabase: Client, author_query: str) -> int:
    slug = normalize_author(author_query)
    result = (
        supabase.table("quotes")
        .select("id", count="exact")
        .eq("active", True)
        .ilike("author_slug", f"%{slug}%")
        .execute()
    )
    return result.count or 0


def list_quotes_by_author(
    supabase: Client,
    author_query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    slug = normalize_author(author_query)
    capped_limit = max(1, min(limit, 50))
    result = (
        supabase.table("quotes")
        .select("id, text, author, tags, active")
        .eq("active", True)
        .ilike("author_slug", f"%{slug}%")
        .order("created_at", desc=True)
        .limit(capped_limit)
        .execute()
    )
    return result.data or []


def upsert_quote_manual(
    supabase: Client,
    text: str,
    author: str,
    tags: list[str],
) -> dict[str, Any]:
    if not text.strip() or not author.strip():
        raise ValueError("text y author son obligatorios.")

    normalized_text = normalize_text_for_hash(text)
    text_hash = compute_text_hash(normalized_text)
    author_slug = normalize_author(author)
    now = datetime.now(timezone.utc).isoformat()

    payload = {
        "text": text.strip(),
        "text_hash": text_hash,
        "author": author.strip(),
        "author_slug": author_slug,
        "tags": tags,
        "source": "manual",
        "active": True,
        "last_seen_at": now,
    }

    result = (
        supabase.table("quotes")
        .upsert(payload, on_conflict="text_hash", ignore_duplicates=True)
        .execute()
    )
    return (result.data[0] if result.data else {})


def set_quote_active_status(supabase: Client, quote_id: str, active: bool) -> None:
    supabase.table("quotes").update({"active": active}).eq("id", quote_id).execute()
