"""Envío de correos de novedades y escalaciones con Resend."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import resend
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from tenacity import RetryError

from app.config import Settings

logger = logging.getLogger(__name__)


def configure_resend(settings: Settings) -> None:
    resend.api_key = settings.resend_api_key


def _group_quotes_by_tag(quotes: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for q in quotes:
        for tag in q.get("tags", []):
            grouped[tag].append(q)
    return dict(grouped)


def _build_novelty_html(grouped: dict[str, list[dict[str, Any]]]) -> str:
    total = sum(len(qs) for qs in grouped.values())
    sections = []
    for tag in sorted(grouped.keys()):
        quotes = grouped[tag]
        sections.append(f'<h2 style="color:#2563eb;">{tag.title()} ({len(quotes)})</h2>')
        items = []
        for q in quotes:
            text = q.get("text", "")
            author = q.get("author", "Desconocido")
            items.append(f'<li><em>"{text}"</em> — {author}</li>')
        sections.append(f"<ul>{''.join(items)}</ul>")
    return f"""<html><body style="font-family:Arial,sans-serif;">
<h1>QuoteBox — {total} frases nuevas detectadas</h1>
{''.join(sections)}
<p style="color:#666;font-size:12px;">Enviado {datetime.now(timezone.utc).isoformat()}</p>
</body></html>"""


def _build_escalation_html(author_name: str, request_count: int) -> str:
    return f"""<html><body style="font-family:Arial,sans-serif;">
<h1>Autor desconocido frecuente: {author_name}</h1>
<p>El autor <strong>{author_name}</strong> fue solicitado <strong>{request_count}</strong> veces
y no tiene frases en el sistema.</p>
<p>Panel admin: <a href="#">Cargar frases de {author_name}</a></p>
<p style="color:#666;font-size:12px;">Enviado {datetime.now(timezone.utc).isoformat()}</p>
</body></html>"""


def _build_error_html(context: str, detail: str) -> str:
    return f"""<html><body style="font-family:Arial,sans-serif;">
<h1 style="color:#dc2626;">Error: {context}</h1>
<pre style="background:#f3f4f6;padding:12px;">{detail}</pre>
<p style="color:#666;font-size:12px;">Enviado {datetime.now(timezone.utc).isoformat()}</p>
</body></html>"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(Exception),
)
def _send_with_retry(settings: Settings, params: dict[str, Any]) -> dict[str, Any]:
    resend.Emails.send(params)
    return {"sent": True}


def send_novelty_summary_email(
    settings: Settings,
    grouped_by_tag: dict[str, list[dict[str, Any]]],
) -> str | None:
    if not grouped_by_tag:
        return None

    total = sum(len(qs) for qs in grouped_by_tag.values())
    params = {
        "from": settings.notification_email_from,
        "to": [settings.notification_email_to],
        "subject": f"QuoteBox — {total} frases nuevas detectadas",
        "html": _build_novelty_html(grouped_by_tag),
    }

    try:
        _send_with_retry(settings, params)
        logger.info("Resumen de novedades enviado: %d quotes en %d tags.", total, len(grouped_by_tag))
        return "sent"
    except RetryError:
        logger.exception("Fallo al enviar resumen de novedades tras 3 intentos.")
        return None


def send_escalation_email(
    settings: Settings,
    author_name: str,
    request_count: int,
) -> str | None:
    params = {
        "from": settings.notification_email_from,
        "to": [settings.escalation_email_to],
        "subject": f"QuoteBox — Autor desconocido frecuente: {author_name}",
        "html": _build_escalation_html(author_name, request_count),
    }

    try:
        _send_with_retry(settings, params)
        logger.info("Mail de escalación enviado para autor %s (%d consultas).", author_name, request_count)
        return "sent"
    except RetryError:
        logger.exception("Fallo al enviar escalación para autor %s tras 3 intentos.", author_name)
        return None


def send_error_email(
    settings: Settings,
    context: str,
    detail: str,
) -> str | None:
    params = {
        "from": settings.notification_email_from,
        "to": [settings.notification_email_to],
        "subject": f"QuoteBox — Error: {context}",
        "html": _build_error_html(context, detail),
    }

    try:
        _send_with_retry(settings, params)
        logger.info("Mail de error enviado: %s", context)
        return "sent"
    except RetryError:
        logger.exception("Fallo al enviar mail de error para %s tras 3 intentos.", context)
        return None
