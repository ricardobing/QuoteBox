"""Crawler paginado para extraer frases desde quotes.toscrape.com."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable

import requests
from bs4 import BeautifulSoup

from app.config import Settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RawQuote:
    """Representa una frase extraída del HTML antes de persistir."""

    text: str
    author: str
    tags: list[str]


@dataclass(slots=True)
class CrawlResult:
    """Resultado bruto de crawling paginado."""

    pages_scraped: int
    quotes: list[RawQuote]


def parse_quotes_from_html(html: str) -> list[RawQuote]:
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as exc:
        raise RuntimeError("No se pudo parsear el HTML de quotes.") from exc

    quotes: list[RawQuote] = []
    for quote_div in soup.select("div.quote"):
        text_el = quote_div.select_one("span.text")
        author_el = quote_div.select_one("small.author")
        tag_els = quote_div.select("div.tags a.tag")

        if not text_el or not author_el:
            logger.warning("Quote incompleta detectada, se descarta.")
            continue

        text = text_el.get_text(strip=True)
        text = text.strip("\u201c\u201d\u0022")  # comillas tipográficas y normales
        author = author_el.get_text(strip=True)
        tags = [t.get_text(strip=True).lower() for t in tag_els]

        quotes.append(RawQuote(text=text, author=author, tags=tags))

    return quotes


def crawl_all_quotes(session: requests.Session, settings: Settings) -> CrawlResult:
    base_url = settings.scrape_base_url.rstrip("/")
    page_url = f"{base_url}/page/1/"
    visited: set[str] = set()
    all_quotes: list[RawQuote] = []
    pages = 0

    while page_url:
        if page_url in visited:
            raise RuntimeError(f"Loop de paginación detectado en {page_url}.")

        visited.add(page_url)

        try:
            resp = session.get(page_url, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Error HTTP en {page_url}: {exc}") from exc

        page_quotes = parse_quotes_from_html(resp.text)
        all_quotes.extend(page_quotes)
        pages += 1

        soup = BeautifulSoup(resp.text, "html.parser")
        next_link = soup.select_one("li.next a")
        if next_link and next_link.get("href"):
            next_href: str = next_link["href"]
            page_url = f"{base_url}{next_href}" if next_href.startswith("/") else next_href
        else:
            page_url = None

    logger.info("Crawling completo: %d páginas, %d quotes extraídas.", pages, len(all_quotes))
    return CrawlResult(pages_scraped=pages, quotes=all_quotes)
