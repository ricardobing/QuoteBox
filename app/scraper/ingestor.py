"""Normalización e ingesta idempotente de frases en Supabase."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from supabase import Client

from app.scraper.crawler import RawQuote

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class IngestResult:
    """Métricas de una corrida de ingesta."""

    quotes_seen: int
    quotes_inserted: int


def normalize_text_for_hash(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text.strip().lower())
    return collapsed


def compute_text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_author(author: str) -> str:
    return re.sub(r"\s+", " ", author.strip().lower())


def upsert_quotes_idempotent(
    supabase: Client,
    quotes: list[RawQuote],
    active_tags: set[str],
) -> IngestResult:
    filtered: list[RawQuote] = []
    for q in quotes:
        if set(q.tags) & active_tags:
            filtered.append(q)

    if not filtered:
        return IngestResult(quotes_seen=0, quotes_inserted=0)

    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for q in filtered:
        normalized_text = normalize_text_for_hash(q.text)
        text_hash = compute_text_hash(normalized_text)
        author_slug = normalize_author(q.author)
        rows.append({
            "text": q.text,
            "text_hash": text_hash,
            "author": q.author,
            "author_slug": author_slug,
            "tags": q.tags,
            "source": "scraper",
            "active": True,
            "last_seen_at": now,
        })

    inserted = 0
    for row in rows:
        try:
            result = (
                supabase.table("quotes")
                .upsert(row, on_conflict="text_hash", ignore_duplicates=True)
                .execute()
            )
            if result.data:
                inserted += len(result.data)
        except Exception as exc:
            logger.warning("Error insertando quote de %s: %s", row.get("author"), exc)

    logger.info("Ingesta: %d quotes filtradas de %d totales, %d nuevas insertadas.",
                len(filtered), len(quotes), inserted)
    return IngestResult(quotes_seen=len(quotes), quotes_inserted=inserted)


def record_scrape_run(
    supabase: Client,
    status: str,
    pages_scraped: int,
    quotes_found: int,
    quotes_new: int,
    error_detail: str | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "status": status,
        "pages_scraped": pages_scraped,
        "quotes_found": quotes_found,
        "quotes_new": quotes_new,
        "started_at": now,
        "finished_at": now,
    }
    if error_detail:
        payload["error_detail"] = error_detail

    try:
        supabase.table("scrape_runs").insert(payload).execute()
    except Exception as exc:
        logger.error("Fallo al registrar scrape_run: %s", exc)
        raise
