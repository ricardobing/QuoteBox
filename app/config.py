"""Configuración central de la aplicación via variables de entorno."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Representa todas las variables de entorno necesarias para QuoteBox."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Supabase
    supabase_url: str = Field(alias="SUPABASE_URL")
    supabase_anon_key: str = Field(alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_db_url: str | None = Field(default=None, alias="SUPABASE_DB_URL")

    # Scraping
    scrape_base_url: str = Field(alias="SCRAPE_BASE_URL")
    scrape_username: str = Field(alias="SCRAPE_USERNAME")
    scrape_password: str = Field(alias="SCRAPE_PASSWORD")
    scrape_interval_hours: int = Field(default=24, alias="SCRAPE_INTERVAL_HOURS")

    # Twilio
    twilio_account_sid: str = Field(alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(alias="TWILIO_AUTH_TOKEN")
    twilio_whatsapp_from: str = Field(alias="TWILIO_WHATSAPP_FROM")
    twilio_skip_validation: bool = Field(default=False, alias="TWILIO_SKIP_VALIDATION")

    # Resend
    resend_api_key: str = Field(alias="RESEND_API_KEY")
    notification_email_to: str = Field(alias="NOTIFICATION_EMAIL_TO")
    notification_email_from: str = Field(alias="NOTIFICATION_EMAIL_FROM")
    escalation_email_to: str = Field(alias="ESCALATION_EMAIL_TO")

    # Lógica
    unknown_author_threshold: int = Field(default=2, alias="UNKNOWN_AUTHOR_THRESHOLD")

    # Seguridad
    webhook_secret: str = Field(alias="WEBHOOK_SECRET")

    # Integración admin
    fastapi_base_url: str = Field(default="http://localhost:8000", alias="FASTAPI_BASE_URL")


def get_settings() -> Settings:
    """Construye y retorna la configuración tipada de la aplicación."""
    return Settings()
