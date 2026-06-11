"""Router para webhooks de Twilio y flujo de ingesta manual."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from twilio.request_validator import RequestValidator

from app.models.schemas import GenericWebhookResponse, ManualIngestWebhookPayload
from app.services.escalation import (
    normalize_author_query,
    process_unknown_author_escalation,
    register_unknown_author_request,
)
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

    proto = request.headers.get("x-forwarded-proto", "https")
    host = request.headers.get("x-forwarded-host", request.headers.get("host", ""))
    url = f"{proto}://{host}{request.url.path}"

    if settings.twilio_skip_validation:
        logger.warning("TWILIO_SKIP_VALIDATION=true — firma no verificada para %s", from_phone)
    else:
        validator = RequestValidator(settings.twilio_auth_token)
        if not validator.validate(url, dict(form_data), signature):
            logger.warning("Firma Twilio invalida para request desde %s (url=%s)", from_phone, url)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Twilio signature")

    parsed = parse_whatsapp_message(str(body))
    logger.info("WhatsApp: from=%s intent=%s author=%s", from_phone, parsed.intent.value, parsed.author_query)

    if parsed.intent == WhatsAppIntent.COUNT_BY_AUTHOR and parsed.author_query:
        count = count_quotes_by_author(supabase, parsed.author_query)
        reply = build_count_response(parsed.author_query, count)
        if count == 0:
            try:
                register_unknown_author_request(supabase, parsed.author_query, str(from_phone))
                process_unknown_author_escalation(supabase, settings, parsed.author_query)
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
                process_unknown_author_escalation(supabase, settings, parsed.author_query)
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
    from app.config import get_settings
    from app.services.email import configure_resend, send_error_email
    from app.services.quotes import upsert_quote_manual

    settings = get_settings()

    if not x_webhook_secret or x_webhook_secret != settings.webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook secret.",
        )

    record = payload.get("record", {})
    record_id = record.get("id")
    text = record.get("text", "")
    author = record.get("author", "")
    tags = record.get("tags", [])

    supabase = None
    try:
        from app.database import get_supabase_client
        supabase = get_supabase_client(settings)
    except Exception as exc:
        logger.exception("No se pudo conectar a Supabase para manual ingest")
        raise HTTPException(status_code=500, detail=str(exc))

    if not text or not author:
        error_detail = f"Validacion fallida: text o author vacio. record_id={record_id}"
        logger.warning(error_detail)
        try:
            supabase.table("manual_queue").update({
                "status": "error",
                "error_detail": error_detail,
                "processed_at": "now()",
            }).eq("id", record_id).execute()
        except Exception:
            logger.exception("No se pudo actualizar manual_queue como error")
        try:
            configure_resend(settings)
            send_error_email(settings, "Manual ingest validation failed", error_detail)
        except Exception:
            logger.exception("Error enviando email de error manual ingest")
        raise HTTPException(status_code=422, detail=error_detail)

    try:
        upsert_quote_manual(supabase, text, author, tags)
    except Exception as exc:
        error_detail = f"Error en upsert: {exc}"
        logger.exception(error_detail)
        supabase.table("manual_queue").update({
            "status": "error",
            "error_detail": str(exc)[:500],
            "processed_at": "now()",
        }).eq("id", record_id).execute()
        try:
            configure_resend(settings)
            send_error_email(settings, "Manual ingest upsert failed", str(exc))
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=error_detail)

    supabase.table("manual_queue").update({
        "status": "approved",
        "processed_at": "now()",
    }).eq("id", record_id).execute()

    logger.info("Manual quote ingested: %s (id=%s)", author, record_id)
    return GenericWebhookResponse(ok=True, detail=f"Quote from {author} ingested")
