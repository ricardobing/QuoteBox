"""Tests para normalizacion e idempotencia del ingestor."""

from __future__ import annotations

from unittest.mock import Mock

from app.scraper.crawler import RawQuote
from app.scraper.ingestor import (
    compute_text_hash,
    normalize_text_for_hash,
    upsert_quotes_idempotent,
)


def test_same_phrase_generates_same_hash_after_normalization() -> None:
    t1 = normalize_text_for_hash("Life is what happens")
    t2 = normalize_text_for_hash("  life   is what   happens  ")
    assert compute_text_hash(t1) == compute_text_hash(t2)


def test_normalize_text_handles_unicode_quotes() -> None:
    raw = "\u201cThe unexamined life\u201d"
    normalized = normalize_text_for_hash(raw)
    assert "the unexamined life" in normalized


def test_normalize_text_different_casing_same_hash() -> None:
    h1 = compute_text_hash(normalize_text_for_hash("HELLO WORLD"))
    h2 = compute_text_hash(normalize_text_for_hash("hello world"))
    assert h1 == h2


def test_upsert_returns_inserted_count() -> None:
    supabase = Mock()
    upsert_mock = Mock()
    upsert_mock.execute.return_value.data = [{"id": "a"}]
    table_mock = Mock()
    table_mock.upsert.return_value = upsert_mock
    supabase.table.return_value = table_mock

    quotes = [RawQuote(text="Quote 1", author="A", tags=["love"])]
    result = upsert_quotes_idempotent(supabase, quotes, {"love"})
    assert result.quotes_inserted == 1


def test_upsert_conflict_returns_zero() -> None:
    supabase = Mock()
    upsert_mock = Mock()
    upsert_mock.execute.return_value.data = []
    table_mock = Mock()
    table_mock.upsert.return_value = upsert_mock
    supabase.table.return_value = table_mock

    quotes = [RawQuote(text="Quote 1", author="A", tags=["love"])]
    result = upsert_quotes_idempotent(supabase, quotes, {"love"})
    assert result.quotes_inserted == 0


def test_upsert_filters_by_active_tags() -> None:
    supabase = Mock()
    upsert_mock = Mock()
    upsert_mock.execute.return_value.data = [{"id": "x"}]
    table_mock = Mock()
    table_mock.upsert.return_value = upsert_mock
    supabase.table.return_value = table_mock

    quotes = [
        RawQuote(text="Quote A", author="A", tags=["love"]),
        RawQuote(text="Quote B", author="B", tags=["sports"]),
    ]
    result = upsert_quotes_idempotent(supabase, quotes, {"love", "humor"})
    assert result.quotes_seen == 2
    assert result.quotes_inserted == 1
