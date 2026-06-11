"""Parseo de intents y respuestas para webhook de WhatsApp."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class WhatsAppIntent(str, Enum):
    COUNT_BY_AUTHOR = "count_by_author"
    LIST_BY_AUTHOR = "list_by_author"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class ParsedWhatsAppMessage:
    intent: WhatsAppIntent
    author_query: str | None


def clean_author_query(raw: str) -> str:
    result = raw.strip().lower()
    result = re.sub(r"^[¿¡\s]+|[?!.,;:\s]+$", "", result)
    prepositions = ["de ", "del ", "en ", "a ", "al ", "sobre ", "para "]
    for prep in prepositions:
        if result.startswith(prep):
            result = result[len(prep):]
            break
    result = result.strip()
    return result if result else raw.strip()


_COUNT_PATTERNS = [
    re.compile(
        r"cu[a\u00e1]ntas?\s+frases?\s+(?:hay\s+)?(?:tiene\s+)?(?:de\s+|en\s+|sobre\s+)?(.+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"cu[a\u00e1]ntas?\s+(?:tiene|ten[e\u00e9]s|hay)\s+(.+)",
        re.IGNORECASE,
    ),
]

_LIST_PATTERNS = [
    re.compile(
        r"(?:cu[a\u00e1]les?\s+son|dame|mostrame|quiero|ver|lista\s+de)\s+"
        r"(?:las?\s+)?(?:frases?\s+)?(?:de\s+|en\s+)?(.+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:frases?\s+|que\s+frases?\s+hay\s+)(?:de\s+|en\s+)?(.+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"^([a-z\u00e1\u00e9\u00ed\u00f3\u00fa\.\-]+(\s+[a-z\u00e1\u00e9\u00ed\u00f3\u00fa\.\-]+){0,1})$",
        re.IGNORECASE,
    ),
]


def parse_whatsapp_message(body: str) -> ParsedWhatsAppMessage:
    normalized = " ".join(body.strip().lower().split())
    if not normalized:
        return ParsedWhatsAppMessage(intent=WhatsAppIntent.UNKNOWN, author_query=None)

    for pattern in _COUNT_PATTERNS:
        m = pattern.match(normalized)
        if m:
            author = clean_author_query(m.group(1))
            return ParsedWhatsAppMessage(
                intent=WhatsAppIntent.COUNT_BY_AUTHOR,
                author_query=author,
            )

    for pattern in _LIST_PATTERNS:
        m = pattern.match(normalized)
        if m:
            author = clean_author_query(m.group(1))
            return ParsedWhatsAppMessage(
                intent=WhatsAppIntent.LIST_BY_AUTHOR,
                author_query=author,
            )

    return ParsedWhatsAppMessage(intent=WhatsAppIntent.UNKNOWN, author_query=normalized)


def build_count_response(author_query: str, count: int) -> str:
    if count == 0:
        return f"No tenemos frases de {author_query} por ahora."
    return f"Hay {count} frases de {author_query}."


def build_list_response(author_query: str, quotes: list[dict[str, Any]], total: int = 0) -> str:
    if not quotes:
        return f"No tenemos frases de {author_query} por ahora."

    lines = [f'{i+1}. "{q["text"]}" -- {q["author"]}' for i, q in enumerate(quotes[:5])]
    response = f"Frases de {author_query}:\n" + "\n".join(lines)
    if total > 5:
        response += f"\n... y {total - 5} mas."
    return response


def build_unknown_author_response(author_query: str) -> str:
    return f"Todavia no tengo frases de {author_query}. Ya registre tu solicitud."


def build_unknown_intent_response() -> str:
    return (
        "No entendi la consulta. Proba:\n"
        '"frases de Einstein"\n'
        '"cuantas frases hay de Wilde?"'
    )


def build_twiml_response(message: str) -> str:
    from twilio.twiml.messaging_response import MessagingResponse

    resp = MessagingResponse()
    resp.message(message)
    return str(resp)
