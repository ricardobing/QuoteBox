"""Punto de entrada FastAPI para QuoteBox."""

from __future__ import annotations

import logging
from collections import defaultdict

from fastapi import FastAPI

from app.config import get_settings
from app.database import get_supabase_client
from app.routers.admin import router as admin_router
from app.routers.health import router as health_router
from app.routers.trigger import router as trigger_router
from app.routers.webhooks import router as webhooks_router
from app.scraper.crawler import crawl_all_quotes
from app.scraper.ingestor import record_scrape_run, upsert_quotes_idempotent
from app.scraper.session import build_http_session, login_with_csrf
from app.scheduler import build_scheduler, register_scrape_job, start_scheduler, stop_scheduler
from app.services.email import configure_resend, send_novelty_summary_email
from app.services.tags import get_active_tags

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    supabase = get_supabase_client(settings)
    scheduler = build_scheduler(settings)
    configure_resend(settings)

    app = FastAPI(title="QuoteBox API", version="0.1.0")
    app.state.settings = settings
    app.state.supabase = supabase
    app.state.scheduler = scheduler

    app.include_router(health_router, tags=["health"])
    app.include_router(trigger_router, tags=["trigger"])
    app.include_router(admin_router, tags=["admin"])
    app.include_router(webhooks_router, tags=["webhooks"])

    def _run_scrape_pipeline() -> None:
        try:
            session = build_http_session()
            login_with_csrf(session, settings)

            crawl_result = crawl_all_quotes(session, settings)
            active_tags = get_active_tags(supabase)

            ingest_result = upsert_quotes_idempotent(supabase, crawl_result.quotes, active_tags)
            record_scrape_run(
                supabase,
                status="success",
                pages_scraped=crawl_result.pages_scraped,
                quotes_found=ingest_result.quotes_seen,
                quotes_new=ingest_result.quotes_inserted,
            )

            if ingest_result.quotes_inserted > 0:
                grouped: dict[str, list[dict]] = defaultdict(list)
                for q in (ingest_result.new_quotes or []):
                    for tag in q.get("tags", []):
                        grouped[tag].append({"text": q.get("text",""), "author": q.get("author",""), "tags": q.get("tags",[])})
                send_novelty_summary_email(settings, dict(grouped))

            logger.info(
                "Pipeline automatico: %d paginas, %d encontradas, %d nuevas.",
                crawl_result.pages_scraped,
                ingest_result.quotes_seen,
                ingest_result.quotes_inserted,
            )
        except Exception:
            logger.exception("Pipeline automatico fallo.")

    @app.on_event("startup")
    def _on_startup() -> None:
        register_scrape_job(scheduler, settings, _run_scrape_pipeline)
        start_scheduler(scheduler)

    @app.on_event("shutdown")
    def _on_shutdown() -> None:
        stop_scheduler(scheduler)

    return app


app = create_app()
