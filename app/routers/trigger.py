"""Router para disparar scraping manualmente."""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Request

from app.config import Settings
from app.models.schemas import ScrapeResult
from app.scraper.crawler import crawl_all_quotes
from app.scraper.ingestor import record_scrape_run, upsert_quotes_idempotent
from app.scraper.session import build_http_session, login_with_csrf
from app.services.email import send_novelty_summary_email
from app.services.tags import get_active_tags

logger = logging.getLogger(__name__)
router = APIRouter()


def _group_quotes_by_tag(quotes, active_tags):
    grouped: dict[str, list[dict]] = defaultdict(list)
    for q in quotes:
        q_tags = set(q.tags) & active_tags
        for tag in q_tags:
            grouped[tag].append({"text": q.text, "author": q.author, "tags": q.tags})
    return dict(grouped)


@router.post("/trigger/scrape", response_model=ScrapeResult)
def trigger_scrape(request: Request) -> ScrapeResult:
    settings: Settings = request.app.state.settings
    supabase = request.app.state.supabase

    started_at = time.monotonic()

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
            try:
                grouped = _group_quotes_by_tag(ingest_result.new_quotes or [], active_tags)
                send_novelty_summary_email(settings, grouped)
            except Exception:
                logger.exception("Error enviando resumen de novedades (no bloqueante).")

        duration = round(time.monotonic() - started_at, 2)
        logger.info(
            "Scrape completado: %d paginas, %d quotes, %d nuevas en %.2fs.",
            crawl_result.pages_scraped,
            ingest_result.quotes_seen,
            ingest_result.quotes_inserted,
            duration,
        )

        return ScrapeResult(
            status="success",
            pages_scraped=crawl_result.pages_scraped,
            quotes_found=ingest_result.quotes_seen,
            quotes_new=ingest_result.quotes_inserted,
        )

    except Exception as exc:
        duration = round(time.monotonic() - started_at, 2)
        error_detail = f"{type(exc).__name__}: {exc}"
        logger.exception("Scrape fallo en %.2fs: %s", duration, error_detail)

        try:
            record_scrape_run(
                supabase,
                status="error",
                pages_scraped=0,
                quotes_found=0,
                quotes_new=0,
                error_detail=error_detail,
            )
        except Exception:
            logger.exception("No se pudo registrar scrape_run de error.")

        raise HTTPException(status_code=500, detail=error_detail)
