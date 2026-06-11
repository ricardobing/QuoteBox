"""Parseo de intents y respuestas para webhook de WhatsApp."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WhatsAppIntent(str, Enum):
    """Intents soportados por el bot."""

    COUNT_BY_AUTHOR = "count_by_author"
    LIST_BY_AUTHOR = "list_by_author"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class ParsedWhatsAppMessage:
    """Resultado del parseo de un mensaje entrante."""

    intent: WhatsAppIntent
    author_query: str | None


def parse_whatsapp_message(body: str) -> ParsedWhatsAppMessage:
    """Parsea un mensaje para detectar intent y autor objetivo.

    Args:
        body: Texto recibido por WhatsApp.

    Returns:
        Objeto tipado con intent detectado.
    """
    _ = body
    return ParsedWhatsAppMessage(intent=WhatsAppIntent.UNKNOWN, author_query=None)


def build_count_response(author_query: str, count: int) -> str:
    """Construye respuesta textual para intent de conteo."""
    return f"Hay {count} frases de {author_query}."


def build_list_response(author_query: str, quotes: list[str]) -> str:
    """Construye respuesta textual para intent de listado."""
    if not quotes:
        return f"No encontré frases de {author_query} por ahora."
    joined = "\n".join(f"- {quote}" for quote in quotes)
    return f"Frases de {author_query}:\n{joined}"


def build_unknown_author_response(author_query: str) -> str:
    """Respuesta estándar cuando no hay frases para el autor solicitado."""
    return f"Todavía no tengo frases de {author_query}. Ya registré tu solicitud 🙌"
