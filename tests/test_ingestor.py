"""Tests base para semántica de idempotencia."""

from __future__ import annotations

from app.scraper.ingestor import compute_text_hash, normalize_text_for_hash


def test_same_phrase_generates_same_hash_after_normalization() -> None:
    """Variaciones de casing/espacios deben converger al mismo hash."""
    t1 = normalize_text_for_hash("Life is what happens")
    t2 = normalize_text_for_hash("  life   is what   happens  ")
    assert compute_text_hash(t1) == compute_text_hash(t2)
