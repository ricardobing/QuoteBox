"""Registro y escalacion de autores desconocidos consultados por WhatsApp."""

from __future__ import annotations

import logging
import re

from supabase import Client

from app.config import Settings
from app.services.email import send_escalation_email

logger = logging.getLogger(__name__)


def normalize_author_query(author_query: str) -> str:
    return re.sub(r"\s+", " ", author_query.strip().lower())


def register_unknown_author_request(
    supabase: Client,
    author_query: str,
    from_phone: str,
) -> None:
    normalized = normalize_author_query(author_query)
    supabase.table("unknown_author_requests").insert({
        "author_query": author_query.strip(),
        "author_normalized": normalized,
        "from_phone": from_phone,
    }).execute()
    logger.info("Unknown author request registrado: %s", normalized)


def count_requests_for_author(supabase: Client, author_normalized: str) -> int:
    result = (
        supabase.table("unknown_author_requests")
        .select("id", count="exact")
        .eq("author_normalized", author_normalized)
        .execute()
    )
    return result.count or 0


def is_author_already_escalated(supabase: Client, author_normalized: str) -> bool:
    result = (
        supabase.table("unknown_author_requests")
        .select("id")
        .eq("author_normalized", author_normalized)
        .eq("escalated", True)
        .limit(1)
        .execute()
    )
    return bool(result.data)


def should_escalate_unknown_author(
    supabase: Client,
    settings: Settings,
    author_query: str,
) -> tuple[bool, int, str]:
    normalized = normalize_author_query(author_query)
    count = count_requests_for_author(supabase, normalized)
    already = is_author_already_escalated(supabase, normalized)
    threshold = settings.unknown_author_threshold
    should = count >= threshold and not already
    return (should, count, normalized)


def mark_author_as_escalated(supabase: Client, author_normalized: str) -> None:
    supabase.table("unknown_author_requests").update({"escalated": True}).eq(
        "author_normalized", author_normalized
    ).execute()


def process_unknown_author_escalation(
    supabase: Client,
    settings: Settings,
    author_query: str,
) -> bool:
    should, count, normalized = should_escalate_unknown_author(
        supabase, settings, author_query
    )
    if not should:
        return False

    send_escalation_email(settings, normalized, count)
    mark_author_as_escalated(supabase, normalized)
    logger.info("Autor %s escalado con %d solicitudes.", normalized, count)
    return True
