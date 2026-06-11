"""Registro y escalación de autores desconocidos consultados por WhatsApp."""

from __future__ import annotations

import re

from supabase import Client

from app.config import Settings


def normalize_author_query(author_query: str) -> str:
    """Normaliza query de autor para agrupación consistente."""
    return re.sub(r"\s+", " ", author_query.strip().lower())


def register_unknown_author_request(supabase: Client, author_query: str, from_phone: str) -> None:
    """Persiste una consulta de autor desconocido.

    Raises:
        RuntimeError: Si falla inserción en tabla de tracking.
    """
    _ = (supabase, author_query, from_phone)


def should_escalate_unknown_author(supabase: Client, settings: Settings, author_query: str) -> tuple[bool, int, str]:
    """Evalúa si corresponde escalar según umbral y estado actual.

    Args:
        supabase: Cliente Supabase.
        settings: Configuración global.
        author_query: Autor consultado por usuario.

    Returns:
        Tuple: (should_escalate, total_requests, author_normalized).

    Raises:
        RuntimeError: Si falla lectura de métricas.
    """
    author_normalized = normalize_author_query(author_query)
    _ = supabase
    return (False, 0, author_normalized)


def mark_author_as_escalated(supabase: Client, author_normalized: str) -> None:
    """Marca registros pendientes de un autor como escalados."""
    _ = (supabase, author_normalized)
