"""Test WhatsApp flow end-to-end"""
from app.config import get_settings
from app.database import get_supabase_client
from app.services.whatsapp import (
    parse_whatsapp_message,
    WhatsAppIntent,
    build_count_response,
    build_list_response,
    build_unknown_intent_response,
    build_twiml_response,
)
from app.services.quotes import count_quotes_by_author, list_quotes_by_author

s = get_settings()
sb = get_supabase_client(s)

tests = [
    "cuantas frases hay de Einstein",
    "frases de Rowling",
    "frases de Nietzsche",
    "que tal todo",
]

for msg in tests:
    p = parse_whatsapp_message(msg)
    print(f'Body: "{msg}" -> {p.intent.value}, author={p.author_query}')

    if p.intent == WhatsAppIntent.COUNT_BY_AUTHOR and p.author_query:
        c = count_quotes_by_author(sb, p.author_query)
        r = build_count_response(p.author_query, c)
        print(f'  Count={c}: {r[:120]}')
    elif p.intent == WhatsAppIntent.LIST_BY_AUTHOR and p.author_query:
        qs = list_quotes_by_author(sb, p.author_query, limit=5)
        t = count_quotes_by_author(sb, p.author_query)
        r = build_list_response(p.author_query, qs, t)
        print(f'  Total={t}, Returning {len(qs)}: {r[:200]}')
    else:
        r = build_unknown_intent_response()
        print(f'  {r[:120]}')

    twiml = build_twiml_response(r)
    print(f'  TwiML OK: {len(twiml)} bytes')
    print()
