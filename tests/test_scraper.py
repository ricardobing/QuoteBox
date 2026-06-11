"""Tests base para módulo de scraping."""

from __future__ import annotations

from app.scraper.ingestor import compute_text_hash, normalize_author, normalize_text_for_hash


def test_normalize_text_for_hash_collapses_whitespace() -> None:
    """Debe normalizar espacios, trim y lowercase."""
    raw = "  Hello   WORLD \n  from   QuoteBox  "
    normalized = normalize_text_for_hash(raw)
    assert normalized == "hello world from quotebox"


def test_compute_text_hash_is_deterministic() -> None:
    """El hash del mismo input debe ser idéntico en cada llamada."""
    base = "consistency"
    assert compute_text_hash(base) == compute_text_hash(base)


def test_normalize_author() -> None:
    """El autor se normaliza para matching robusto."""
    assert normalize_author("  Albert   Einstein ") == "albert einstein"
