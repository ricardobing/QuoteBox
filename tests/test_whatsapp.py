"""Tests para parseo de WhatsApp y TwiML."""

from __future__ import annotations

from app.services.whatsapp import (
    WhatsAppIntent,
    build_list_response,
    build_twiml_response,
    build_unknown_author_response,
    clean_author_query,
    parse_whatsapp_message,
)


def test_build_list_response_with_empty_quotes() -> None:
    response = build_list_response("Einstein", [])
    assert "No tenemos frases" in response


def test_build_unknown_author_response_mentions_author() -> None:
    response = build_unknown_author_response("Einstein")
    assert "Einstein" in response


def test_clean_author_removes_punctuation() -> None:
    assert clean_author_query("einstein?") == "einstein"
    assert clean_author_query("borges.") == "borges"
    assert clean_author_query("neruda!") == "neruda"


def test_clean_author_removes_leading_preposition() -> None:
    assert clean_author_query("de einstein") == "einstein"
    assert clean_author_query("en einstein") == "einstein"
    assert clean_author_query("de albert einstein") == "albert einstein"
    assert clean_author_query("sobre nietzsche") == "nietzsche"


def test_clean_author_strips_spaces() -> None:
    assert clean_author_query("  einstein  ") == "einstein"


def test_parse_intent_count_de_einstein() -> None:
    p = parse_whatsapp_message("cuantas frases hay de Einstein")
    assert p.intent == WhatsAppIntent.COUNT_BY_AUTHOR
    assert p.author_query == "einstein"


def test_parse_intent_count_de_einstein_question() -> None:
    p = parse_whatsapp_message("Cuantas frases hay de Einstein?")
    assert p.intent == WhatsAppIntent.COUNT_BY_AUTHOR
    assert p.author_query == "einstein"


def test_parse_intent_count_en_einstein() -> None:
    p = parse_whatsapp_message("Cuantas frases hay en Einstein")
    assert p.intent == WhatsAppIntent.COUNT_BY_AUTHOR
    assert p.author_query == "einstein"


def test_parse_intent_list_de_oscar_wilde() -> None:
    p = parse_whatsapp_message("frases de Oscar Wilde")
    assert p.intent == WhatsAppIntent.LIST_BY_AUTHOR
    assert p.author_query == "oscar wilde"


def test_parse_intent_list_de_oscar_wilde_question() -> None:
    p = parse_whatsapp_message("frases de Oscar Wilde?")
    assert p.intent == WhatsAppIntent.LIST_BY_AUTHOR
    assert p.author_query == "oscar wilde"


def test_parse_intent_list_dame_borges() -> None:
    p = parse_whatsapp_message("dame frases de Borges")
    assert p.intent == WhatsAppIntent.LIST_BY_AUTHOR
    assert p.author_query == "borges"


def test_parse_intent_count_tiene_albert_einstein() -> None:
    p = parse_whatsapp_message("cuantas tiene Albert Einstein")
    assert p.intent == WhatsAppIntent.COUNT_BY_AUTHOR
    assert p.author_query == "albert einstein"


def test_parse_intent_list_que_frases_neruda() -> None:
    p = parse_whatsapp_message("que frases hay de Neruda?")
    assert p.intent == WhatsAppIntent.LIST_BY_AUTHOR
    assert p.author_query == "neruda"


def test_parse_intent_list_just_author() -> None:
    p = parse_whatsapp_message("Einstein")
    assert p.intent == WhatsAppIntent.LIST_BY_AUTHOR
    assert p.author_query == "einstein"


def test_parse_intent_unknown() -> None:
    p = parse_whatsapp_message("hola que tal")
    assert p.intent == WhatsAppIntent.UNKNOWN


def test_parse_intent_case_insensitive() -> None:
    p = parse_whatsapp_message("FRASES DE EINSTEIN")
    assert p.intent == WhatsAppIntent.LIST_BY_AUTHOR
    assert p.author_query == "einstein"


def test_twiml_response_format() -> None:
    twiml = build_twiml_response("Hola mundo")
    assert "<Message>" in twiml
    assert "Hola mundo" in twiml
    assert twiml.startswith("<?xml")
    assert "<Response>" in twiml
