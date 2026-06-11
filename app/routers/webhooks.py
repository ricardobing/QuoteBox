"""Router para webhooks de Twilio y flujo de ingesta manual."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.models.schemas import GenericWebhookResponse, ManualIngestWebhookPayload

router = APIRouter()


@router.post("/webhook/whatsapp", response_model=GenericWebhookResponse)
async def whatsapp_webhook(request: Request) -> GenericWebhookResponse:
    """Recibe mensajes entrantes de Twilio WhatsApp.

    Args:
        request: Request raw para parsear form-data en implementación final.

    Returns:
        Confirmación genérica para proveedor webhook.
    """
    _ = request
    return GenericWebhookResponse(ok=True, detail="whatsapp event received")


@router.post("/webhook/manual-ingest", response_model=GenericWebhookResponse)
def manual_ingest_webhook(
    payload: ManualIngestWebhookPayload,
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
) -> GenericWebhookResponse:
    """Recibe eventos de Supabase para procesar cola manual.

    Args:
        payload: Carga mínima con identificador de registro.
        x_webhook_secret: Secret compartido para autenticar origen.

    Raises:
        HTTPException: Si falta secret (placeholder de validación).

    Returns:
        Confirmación de aceptación.
    """
    if x_webhook_secret is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing webhook secret header.",
        )

    _ = payload
    return GenericWebhookResponse(ok=True, detail="manual ingest event received")
