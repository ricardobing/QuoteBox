"""Fixtures compartidas para tests de QuoteBox."""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest


@pytest.fixture(autouse=True)
def default_env() -> Generator[None, None, None]:
    """Inyecta variables mínimas de entorno requeridas en tests.

    Nota:
        Valores dummy: no deben apuntar a recursos reales.
    """
    env = {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_ANON_KEY": "anon",
        "SUPABASE_SERVICE_ROLE_KEY": "service-role",
        "SCRAPE_BASE_URL": "https://quotes.toscrape.com",
        "SCRAPE_USERNAME": "ArchytasUser",
        "SCRAPE_PASSWORD": "123",
        "TWILIO_ACCOUNT_SID": "ACxxxxxxxx",
        "TWILIO_AUTH_TOKEN": "token",
        "TWILIO_WHATSAPP_FROM": "whatsapp:+14155238886",
        "RESEND_API_KEY": "re_x",
        "NOTIFICATION_EMAIL_TO": "team@example.com",
        "NOTIFICATION_EMAIL_FROM": "QuoteBox <noreply@example.com>",
        "ESCALATION_EMAIL_TO": "team@example.com",
        "WEBHOOK_SECRET": "secret",
    }

    original = {key: os.environ.get(key) for key in env}
    for key, value in env.items():
        os.environ[key] = value

    yield

    for key, previous in original.items():
        if previous is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = previous
