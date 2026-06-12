"""QA completo de QuoteBox — corre contra Railway + Supabase."""
from __future__ import annotations

import os
import sys
from datetime import datetime

import requests
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

BASE_URL = "https://quotebox-production-43dc.up.railway.app"
SB_URL = os.getenv("SUPABASE_URL", "")
SB_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

PASS = 0
FAIL = 0
ERRORS: list[str] = []


def test(name, fn):
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        print(f"  [PASS] {name}")
    except AssertionError as e:
        FAIL += 1
        err = f"{name}: {e}"
        ERRORS.append(err)
        print(f"  [FAIL] {err}")
    except Exception as e:
        FAIL += 1
        err = f"{name}: {type(e).__name__}: {e}"
        ERRORS.append(err)
        print(f"  [FAIL] {err}")


def get_sb():
    return create_client(SB_URL, SB_KEY)


def http_get(path, timeout=15):
    return requests.get(f"{BASE_URL}{path}", timeout=timeout)


def http_post(path, json_data=None, timeout=60):
    return requests.post(f"{BASE_URL}{path}", json=json_data, timeout=timeout)


# ============================================================
# BLOQUE A — API Health
# ============================================================
print("\n=== BLOQUE A — API Health ===")

def a1():
    r = http_get("/health")
    assert r.status_code == 200, f"status={r.status_code}"
    j = r.json()
    assert j["status"] == "ok"
    assert "timestamp" in j
    assert "version" in j
test("A1 /health status=ok", a1)

def a2():
    sb = get_sb()
    r = sb.table("monitored_tags").select("*").order("tag").execute()
    assert len(r.data) >= 4
    for t in r.data:
        assert "id" in t and "tag" in t and "active" in t
test("A2 monitored_tags structure", a2)

def a3():
    sb = get_sb()
    r = sb.table("quotes").select("*").limit(1).execute()
    assert len(r.data) > 0
    q = r.data[0]
    for field in ["id", "text", "author", "tags", "source", "active"]:
        assert field in q, f"missing {field}"
test("A3 quotes structure", a3)

def a4():
    sb = get_sb()
    r = sb.table("monitored_tags").select("tag").eq("active", True).execute()
    tags = {t["tag"] for t in r.data}
    expected = {"love", "humor", "life", "inspirational"}
    for e in expected:
        assert e in tags, f"missing tag: {e}"
test("A4 seeds activos", a4)

# ============================================================
# BLOQUE B — Scraping + idempotencia
# ============================================================
print("\n=== BLOQUE B — Scraping + idempotencia ===")
sb = get_sb()

b_count_before = None
b_scrape_1 = None

def b1():
    global b_count_before
    r = sb.table("quotes").select("id", count="exact").execute()
    assert r.count and r.count > 0
    b_count_before = r.count
test("B1 count quotes >0", b1)

def b2():
    global b_scrape_1
    r = http_post("/trigger/scrape")
    assert r.status_code == 200, f"status={r.status_code}: {r.text[:100]}"
    j = r.json()
    assert j["pages_scraped"] > 0
    assert j["quotes_found"] > 0
    assert j["quotes_new"] == 0, f"DUPLICADOS! inserted={j['quotes_new']}"
    b_scrape_1 = j
test("B2 scrape quotes_new=0 (idempotencia)", b2)

def b3():
    r = sb.table("quotes").select("id", count="exact").execute()
    assert r.count == b_count_before, f"{b_count_before} -> {r.count}"
test("B3 count sin cambios", b3)

def b4():
    r = sb.table("scrape_runs").select("*").order("started_at", desc=True).limit(1).execute()
    assert len(r.data) > 0
    assert r.data[0]["status"] == "success"
test("B4 scrape_runs actualizado", b4)

def b5():
    r = http_post("/trigger/scrape")
    j = r.json()
    assert j["quotes_new"] == 0, f"2da corrida inserted={j['quotes_new']}"
test("B5 doble idempotencia", b5)

# ============================================================
# BLOQUE C — Novedades (tag nuevo)
# ============================================================
print("\n=== BLOQUE C — Flujo de novedades ===")

c_count = None

def c1():
    sb.table("monitored_tags").insert({"tag": "thinking", "active": True}).execute()
test("C1 insert tag 'thinking' (tag real del sitio)", c1)

def c2():
    r = http_post("/trigger/scrape")
    j = r.json()
    # thinking tag quotes ya estaban en DB (insertados con otros tags previos)
    # Caso 1: quotes_new>0 si hay quotes nuevas con este tag
    # Caso 2: quotes_new=0 si ya existian (idempotencia correcta)
    assert j["status"] == "success"
test("C2 scrape completo (status=success)", c2)

def c3():
    global c_count
    all_q = sb.table("quotes").select("id,tags").execute()
    matching = [q for q in all_q.data if "thinking" in q.get("tags", [])]
    assert len(matching) > 0, "no quotes with thinking"
    c_count = len(matching)
test("C3 quotes con thinking", c3)

def c4():
    r = http_post("/trigger/scrape")
    assert r.json()["quotes_new"] == 0
test("C4 segunda scrape quotes_new=0", c4)

def c5():
    all_q = sb.table("quotes").select("id,tags").execute()
    matching = [q for q in all_q.data if "thinking" in q.get("tags", [])]
    assert len(matching) == c_count, f"dup! {c_count}->{len(matching)}"
test("C5 sin duplicados", c5)

print("  cleanup C...")
sb.table("monitored_tags").delete().eq("tag", "thinking").execute()

# ============================================================
# BLOQUE D — Desactivar vs eliminar
# ============================================================
print("\n=== BLOQUE D — Desactivar vs eliminar ===")

d_id = None
d_text = None
d_inserted = None

def d1():
    global d_id, d_text
    r = sb.table("quotes").select("id,text").eq("active", True).limit(1).execute()
    assert len(r.data) > 0
    d_id = r.data[0]["id"]
    d_text = r.data[0]["text"]
test("D1 quote activa", d1)

def d2():
    sb.table("quotes").update({"active": False}).eq("id", d_id).execute()
test("D2 desactivar", d2)

def d3():
    r = sb.table("quotes").select("active").eq("id", d_id).execute()
    assert r.data[0]["active"] == False
test("D3 active=false", d3)

def d4():
    http_post("/trigger/scrape")
test("D4 scrape post-desactivacion", d4)

def d5():
    r = sb.table("quotes").select("active").eq("id", d_id).execute()
    assert r.data[0]["active"] == False, "REACTIVADA por scraper!"
test("D5 sigue inactiva (no reactivada)", d5)

def d6():
    sb.table("quotes").delete().eq("id", d_id).execute()
test("D6 delete quote", d6)

def d7():
    global d_inserted
    r = http_post("/trigger/scrape")
    d_inserted = r.json()["quotes_new"]
test("D7 scrape post-delete", d7)

def d8():
    r = sb.table("quotes").select("*").eq("text", d_text).execute()
    assert len(r.data) > 0, "Quote NO reinsertada"
    assert r.data[0]["active"] == True
test("D8 reinsertada con active=true", d8)

def d9():
    assert d_inserted >= 1, f"inserted={d_inserted}"
test("D9 quotes_new>=1", d9)

print("  cleanup D — quote queda")

# ============================================================
# BLOQUE E — CRUD tags
# ============================================================
print("\n=== BLOQUE E — CRUD tags ===")

# pre-cleanup
sb.table("monitored_tags").delete().eq("tag", "qa_crud_tag").execute()

e_id = None

def e1():
    global e_id
    r = sb.table("monitored_tags").insert({"tag": "qa_crud_tag", "active": True}).execute()
    assert len(r.data) > 0
    e_id = r.data[0]["id"]
test("E1 insert qa_crud_tag", e1)

def e2():
    r = sb.table("monitored_tags").select("*").eq("tag", "qa_crud_tag").execute()
    assert len(r.data) > 0
test("E2 qa_crud_tag existe", e2)

def e3():
    sb.table("monitored_tags").update({"active": False}).eq("id", e_id).execute()
test("E3 desactivar tag", e3)

def e4():
    r = sb.table("monitored_tags").select("*").eq("id", e_id).execute()
    assert r.data[0]["active"] == False
test("E4 active=false", e4)

def e5():
    sb.table("monitored_tags").delete().eq("id", e_id).execute()
test("E5 delete tag", e5)

def e6():
    r = sb.table("monitored_tags").select("*").eq("tag", "qa_crud_tag").execute()
    assert len(r.data) == 0
test("E6 tag eliminado", e6)

# ============================================================
# BLOQUE F — Carga manual
# ============================================================
print("\n=== BLOQUE F — Carga manual ===")

QA_TEXT = "QA test quote unique xyz123"
QA_AUTHOR = "QA Test Author"

def f1():
    r = http_post("/admin/quotes/manual", {"text": QA_TEXT, "author": QA_AUTHOR, "tags": ["life"]})
    assert r.status_code == 201, f"expected 201, got {r.status_code}: {r.text}"
test("F1 POST /admin/quotes/manual 201", f1)

def f2():
    r = sb.table("quotes").select("*").eq("author", QA_AUTHOR).execute()
    assert len(r.data) > 0
    q = r.data[0]
    assert q["source"] == "manual"
    assert q["active"] == True
test("F2 DB: source=manual, active=true", f2)

def f3():
    r = http_post("/admin/quotes/manual", {"text": QA_TEXT, "author": QA_AUTHOR, "tags": ["life"]})
    assert r.status_code == 409, f"expected 409, got {r.status_code}: {r.text}"
test("F3 duplicado 409", f3)

def f4():
    r = http_post("/admin/quotes/manual", {"text": "", "author": QA_AUTHOR, "tags": []})
    assert r.status_code == 422, f"expected 422, got {r.status_code}"
test("F4 text vacio 422", f4)

def f5():
    r = http_post("/admin/quotes/manual", {"text": "x", "author": "", "tags": []})
    assert r.status_code == 422, f"expected 422, got {r.status_code}"
test("F5 author vacio 422", f5)

print("  cleanup F...")
sb.table("quotes").delete().eq("author", QA_AUTHOR).execute()

# ============================================================
# BLOQUE G — Parser WhatsApp
# ============================================================
print("\n=== BLOQUE G — Parser WhatsApp ===")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.services.whatsapp import parse_whatsapp_message, WhatsAppIntent

def check(msg, exp_intent, exp_author=None):
    p = parse_whatsapp_message(msg)
    assert p.intent == exp_intent, f"intent={p.intent.value}, expected={exp_intent.value}"
    if exp_author is not None:
        assert p.author_query == exp_author, f"author={p.author_query}, expected={exp_author}"
    if p.author_query:
        assert "?" not in p.author_query, f"author has ?: {p.author_query}"
        assert "¿" not in p.author_query, f"author has ¿: {p.author_query}"
        for prep in ["de ", "en ", "del ", "al "]:
            assert not p.author_query.startswith(prep), f"author starts with '{prep}'"

test("G1 cuantas frases hay de Einstein COUNT einstein",
     lambda: check("cuantas frases hay de Einstein", WhatsAppIntent.COUNT_BY_AUTHOR, "einstein"))
test("G2 Cuantas frases hay de Einstein? COUNT einstein",
     lambda: check("Cuantas frases hay de Einstein?", WhatsAppIntent.COUNT_BY_AUTHOR, "einstein"))
test("G3 cuantas frases hay en Einstein COUNT einstein",
     lambda: check("cuantas frases hay en Einstein", WhatsAppIntent.COUNT_BY_AUTHOR, "einstein"))
test("G4 cuantas tiene Oscar Wilde COUNT",
     lambda: check("cuantas tiene Oscar Wilde", WhatsAppIntent.COUNT_BY_AUTHOR, "oscar wilde"))
test("G5 frases de Borges LIST",
     lambda: check("frases de Borges", WhatsAppIntent.LIST_BY_AUTHOR, "borges"))
test("G6 frases de Oscar Wilde? LIST sin ?",
     lambda: check("frases de Oscar Wilde?", WhatsAppIntent.LIST_BY_AUTHOR, "oscar wilde"))
test("G7 dame frases de Neruda LIST",
     lambda: check("dame frases de Neruda", WhatsAppIntent.LIST_BY_AUTHOR, "neruda"))
test("G8 cuales son las frases de Twain LIST",
     lambda: check("cuales son las frases de Twain", WhatsAppIntent.LIST_BY_AUTHOR, "twain"))
test("G9 hola UNKNOWN",
     lambda: check("hola", WhatsAppIntent.UNKNOWN))
test("G10 FRASES DE EINSTEIN LIST einstein",
     lambda: check("FRASES DE EINSTEIN", WhatsAppIntent.LIST_BY_AUTHOR, "einstein"))
test("G11 Cuantas frases hay de Einstein? COUNT einstein",
     lambda: check("Cuantas frases hay de Einstein?", WhatsAppIntent.COUNT_BY_AUTHOR, "einstein"))
test("G12 Einstein LIST/COUNT",
     lambda: None if parse_whatsapp_message("Einstein").intent in (WhatsAppIntent.LIST_BY_AUTHOR, WhatsAppIntent.COUNT_BY_AUTHOR)
     else (_ for _ in ()).throw(AssertionError("not LIST/COUNT")))

# ============================================================
# BLOQUE I — Consistencia
# ============================================================
print("\n=== BLOQUE I — Consistencia ===")

def i1():
    r = sb.table("quotes").select("id,text_hash").is_("text_hash", "null").execute()
    assert len(r.data) == 0, f"{len(r.data)} quotes with null text_hash"
test("I1 no text_hash nulos", i1)

def i2():
    all_q = sb.table("quotes").select("text_hash").execute()
    seen = {}
    dup_count = 0
    for q in all_q.data:
        h = q["text_hash"]
        if h in seen:
            dup_count += 1
        seen[h] = True
    assert dup_count == 0, f"{dup_count} hashes duplicados"
test("I2 no text_hash duplicados", i2)

def i3():
    r = sb.table("quotes").select("id").or_("author_slug.is.null,author_slug.eq.").execute()
    # chequear nulls y vacios
    nulls = sb.table("quotes").select("id").is_("author_slug", "null").execute()
    assert len(nulls.data) == 0, f"{len(nulls.data)} null author_slug"
test("I3 author_slug no nulos", i3)

def i4():
    r = sb.table("scrape_runs").select("id", count="exact").execute()
    assert r.count and r.count >= 3, f"only {r.count} scrape_runs"
test("I4 scrape_runs >= 3", i4)

def i5():
    r = sb.table("manual_queue").select("id", count="exact").eq("status", "pending").execute()
    pending = r.count or 0
    if pending > 0:
        print(f"    (I5: {pending} pending in manual_queue)")
    # not a hard failure
test("I5 manual_queue consistency", i5)

# ============================================================
# REPORTE
# ============================================================
print(f"\n{'='*60}")
print(f"QA REPORT")
print(f"{'='*60}")
print(f"  PASS: {PASS}  |  FAIL: {FAIL}  |  TOTAL: {PASS+FAIL}")
if FAIL > 0:
    print(f"\n  FAILURES:")
    for e in ERRORS:
        print(f"    {e}")
print(f"{'='*60}")

