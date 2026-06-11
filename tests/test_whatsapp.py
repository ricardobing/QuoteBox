"""Tests base para parseo y respuestas de WhatsApp."""

from __future__ import annotations

from app.services.whatsapp import build_list_response, build_unknown_author_response


def test_build_list_response_with_empty_quotes() -> None:
    """Cuando no hay frases, la respuesta debe indicarlo explícitamente."""
    response = build_list_response("Einstein", [])
    assert "No encontré frases" in response


def test_build_unknown_author_response_mentions_author() -> None:
    """La respuesta de autor desconocido debe incluir el nombre consultado."""
    response = build_unknown_author_response("Einstein")
    assert "Einstein" in response
