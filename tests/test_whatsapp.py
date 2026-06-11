"""Tests para parseo de WhatsApp y TwiML."""

from __future__ import annotations

from app.services.whatsapp import (
    WhatsAppIntent,
    build_list_response,
    build_twiml_response,
    build_unknown_author_response,
    parse_whatsapp_message,
)


def test_build_list_response_with_empty_quotes() -> None:
    response = build_list_response("Einstein", [])
    assert "No tenemos frases" in response


def test_build_unknown_author_response_mentions_author() -> None:
    response = build_unknown_author_response("Einstein")
    assert "Einstein" in response


def test_parse_intent_count() -> None:
    p = parse_whatsapp_message("cuantas frases hay de Einstein")
    assert p.intent == WhatsAppIntent.COUNT_BY_AUTHOR
    assert p.author_query == "einstein"


def test_parse_intent_count_variant() -> None:
    p = parse_whatsapp_message("cuantas tiene Rowling")
    assert p.intent == WhatsAppIntent.COUNT_BY_AUTHOR
    assert p.author_query == "rowling"


def test_parse_intent_list() -> None:
    p = parse_whatsapp_message("frases de Borges")
    assert p.intent == WhatsAppIntent.LIST_BY_AUTHOR
    assert p.author_query == "borges"


def test_parse_intent_list_variant() -> None:
    p = parse_whatsapp_message("dame frases de Wilde")
    assert p.intent == WhatsAppIntent.LIST_BY_AUTHOR
    assert p.author_query == "wilde"


def test_parse_intent_list_cuales_son() -> None:
    p = parse_whatsapp_message("cuales son de Einstein")
    assert p.intent == WhatsAppIntent.LIST_BY_AUTHOR
    assert p.author_query == "einstein"


def test_parse_intent_unknown() -> None:
    p = parse_whatsapp_message("hola que tal")
    assert p.intent == WhatsAppIntent.UNKNOWN
    assert p.author_query == "hola que tal"


def test_parse_intent_case_insensitive() -> None:
    p = parse_whatsapp_message("FRASES DE EINSTEIN")
    assert p.intent == WhatsAppIntent.LIST_BY_AUTHOR
    assert p.author_query == "einstein"


def test_parse_intent_accents() -> None:
    p = parse_whatsapp_message("cuantas frases hay de Garcia Marquez")
    assert p.intent == WhatsAppIntent.COUNT_BY_AUTHOR


def test_twiml_response_format() -> None:
    twiml = build_twiml_response("Hola mundo")
    assert "<Message>" in twiml
    assert "Hola mundo" in twiml
    assert twiml.startswith("<?xml")
    assert "<Response>" in twiml
