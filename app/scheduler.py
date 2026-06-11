"""Inicialización y control del scheduler de scraping."""

from __future__ import annotations

import logging
from typing import Callable

from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import Settings
from app.database import get_sqlalchemy_engine

logger = logging.getLogger(__name__)


def build_scheduler(settings: Settings) -> BackgroundScheduler:
    """Construye el scheduler con job store persistente o en memoria.

    Args:
        settings: Configuración de entorno.

    Returns:
        Instancia de `BackgroundScheduler` lista para iniciar.
    """
    engine = get_sqlalchemy_engine(settings)

    if engine is not None:
        jobstores = {"default": SQLAlchemyJobStore(engine=engine)}
    else:
        jobstores = {"default": MemoryJobStore()}

    scheduler = BackgroundScheduler(jobstores=jobstores, timezone="UTC")
    return scheduler


def register_scrape_job(
    scheduler: BackgroundScheduler,
    settings: Settings,
    scrape_callable: Callable[[], None],
) -> None:
    """Registra el job periódico de scraping.

    Args:
        scheduler: Scheduler activo.
        settings: Configuración global.
        scrape_callable: Función sin parámetros que ejecuta el pipeline.

    Raises:
        RuntimeError: Si no se puede registrar el job.
    """
    try:
        scheduler.add_job(
            scrape_callable,
            trigger="interval",
            hours=settings.scrape_interval_hours,
            id="periodic_scrape",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300,
        )
        logger.info("Job de scraping registrado cada %s horas.", settings.scrape_interval_hours)
    except Exception as exc:  # pragma: no cover - placeholder
        raise RuntimeError("Error registrando job de scraping.") from exc


def start_scheduler(scheduler: BackgroundScheduler) -> None:
    """Inicia el scheduler si aún no está en ejecución."""
    if not scheduler.running:
        scheduler.start()


def stop_scheduler(scheduler: BackgroundScheduler) -> None:
    """Detiene el scheduler de forma segura."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
