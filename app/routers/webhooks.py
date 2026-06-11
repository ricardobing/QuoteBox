"""Router para webhooks de Twilio y flujo de ingesta manual."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from twilio.request_validator import RequestValidator

from app.models.schemas import GenericWebhookResponse, ManualIngestWebhookPayload
from app.services.escalation import normalize_author_query, register_unknown_author_request
from app.services.quotes import count_quotes_by_author, list_quotes_by_author
from app.services.whatsapp import (
    WhatsAppIntent,
    build_count_response,
    build_list_response,
    build_twiml_response,
    build_unknown_author_response,
    build_unknown_intent_response,
    parse_whatsapp_message,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request) -> Response:
    form_data = await request.form()
    body = form_data.get("Body", "")
    from_phone = form_data.get("From", "")
    signature = request.headers.get("X-Twilio-Signature", "")

    settings = request.app.state.settings
    supabase = request.app.state.supabase

    url = str(request.url)
    validator = RequestValidator(settings.twilio_auth_token)
    if not validator.validate(url, dict(form_data), signature):
        logger.warning("Firma Twilio invalida para request desde %s", from_phone)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Twilio signature")

    parsed = parse_whatsapp_message(str(body))
    logger.info("WhatsApp: from=%s intent=%s author=%s", from_phone, parsed.intent.value, parsed.author_query)

    if parsed.intent == WhatsAppIntent.COUNT_BY_AUTHOR and parsed.author_query:
        count = count_quotes_by_author(supabase, parsed.author_query)
        reply = build_count_response(parsed.author_query, count)
        if count == 0:
            try:
                register_unknown_author_request(supabase, parsed.author_query, str(from_phone))
            except Exception:
                logger.exception("Error registrando unknown author request.")

    elif parsed.intent == WhatsAppIntent.LIST_BY_AUTHOR and parsed.author_query:
        quotes = list_quotes_by_author(supabase, parsed.author_query, limit=50)
        total = count_quotes_by_author(supabase, parsed.author_query)
        if quotes:
            reply = build_list_response(parsed.author_query, quotes, total)
        else:
            reply = build_unknown_author_response(parsed.author_query)
            try:
                register_unknown_author_request(supabase, parsed.author_query, str(from_phone))
            except Exception:
                logger.exception("Error registrando unknown author request.")

    elif parsed.intent == WhatsAppIntent.UNKNOWN:
        reply = build_unknown_intent_response()

    else:
        reply = build_unknown_intent_response()

    twiml = build_twiml_response(reply)
    return Response(content=twiml, media_type="application/xml")


@router.post("/webhook/manual-ingest", response_model=GenericWebhookResponse)
def manual_ingest_webhook(
    payload: dict[str, Any],
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
) -> GenericWebhookResponse:
    settings = None
    try:
        from app.config import get_settings  # noqa: F811
        settings = get_settings()
    except Exception:
        pass

    if not x_webhook_secret or (settings and x_webhook_secret != settings.webhook_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook secret.",
        )

    _ = payload
    return GenericWebhookResponse(ok=True, detail="manual ingest event received")
