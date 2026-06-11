"""Clientes y utilidades de acceso a datos (Supabase / SQLAlchemy)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from supabase import Client, create_client

from app.config import Settings

logger = logging.getLogger(__name__)


def get_supabase_client(settings: Settings) -> Client:
    """Crea cliente Supabase con service role key.

    Args:
        settings: Configuración global de la aplicación.

    Returns:
        Cliente Supabase autenticado con permisos de backend.

    Raises:
        ValueError: Si faltan variables críticas de Supabase.
    """
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise ValueError("Supabase URL/service role key no configurados.")

    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_sqlalchemy_engine(settings: Settings) -> Engine | None:
    """Crea un engine SQLAlchemy para job store del scheduler.

    Args:
        settings: Configuración global de la aplicación.

    Returns:
        Engine SQLAlchemy si hay `SUPABASE_DB_URL`, de lo contrario `None`.

    Raises:
        RuntimeError: Si la URL existe pero falla la construcción del engine.
    """
    if not settings.supabase_db_url:
        logger.warning("SUPABASE_DB_URL no definido; se usará MemoryJobStore.")
        return None

    try:
        return create_engine(settings.supabase_db_url, pool_pre_ping=True)
    except Exception as exc:  # pragma: no cover - placeholder
        raise RuntimeError("No se pudo crear SQLAlchemy engine para scheduler.") from exc


def healthcheck_database(_: Client) -> dict[str, Any]:
    """Ejecuta una verificación básica de conectividad de base de datos.

    Nota:
        Función placeholder: se implementará la consulta real en etapa posterior.

    Returns:
        Resultado básico de healthcheck.
    """
    return {"database": "ok"}
