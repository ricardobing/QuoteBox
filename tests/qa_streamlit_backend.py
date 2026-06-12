"""QA de endpoints que consume Streamlit admin."""
from __future__ import annotations

import sys
import os
import time
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "https://quotebox-production-43dc.up.railway.app"

def test(name, fn):
    try:
        fn()
        print(f"  [PASS] {name}")
    except AssertionError as e:
        print(f"  [FAIL] {name}: {e}")
    except Exception as e:
        print(f"  [FAIL] {name}: {type(e).__name__}: {e}")

def http_get(path, timeout=10):
    return requests.get(f"{BASE_URL}{path}", timeout=timeout)

def http_post(path, json_data=None, timeout=60):
    return requests.post(f"{BASE_URL}{path}", json=json_data, timeout=timeout)

print("=== S1 — Home page load simulation ===")
t0 = time.time()
r1 = http_get("/health"); assert r1.status_code == 200
r2 = http_get("/health"); assert r2.status_code == 200  # monitored_tags via DB
dur = time.time() - t0
test("S1 endpoints respond in <3s", lambda: None if dur < 3 else (_ for _ in ()).throw(AssertionError(f"took {dur:.1f}s")))

print("\n=== S2 — Trigger scrape ===")
t0 = time.time()
r = http_post("/trigger/scrape")
dur = time.time() - t0
assert r.status_code == 200
assert r.json()["status"] == "success"
test("S2 scrape in <30s", lambda: None if dur < 30 else (_ for _ in ()).throw(AssertionError(f"took {dur:.1f}s")))

print("\n=== S3 — Tag CRUD flow ===")
from app.database import get_supabase_client
from app.config import get_settings
sb = get_supabase_client(get_settings())

sb.table("monitored_tags").delete().eq("tag", "qa_s3_tag").execute()
r1 = sb.table("monitored_tags").insert({"tag": "qa_s3_tag", "active": True}).execute()
def s3a(): assert len(r1.data) > 0
test("S3a create tag", s3a)

tag_id = r1.data[0]["id"]
sb.table("monitored_tags").update({"active": False}).eq("id", tag_id).execute()
r2 = sb.table("monitored_tags").select("active").eq("id", tag_id).execute()
def s3b(): assert r2.data[0]["active"] == False
test("S3b toggle active", s3b)

sb.table("monitored_tags").delete().eq("id", tag_id).execute()
r3 = sb.table("monitored_tags").select("*").eq("tag", "qa_s3_tag").execute()
def s3c(): assert len(r3.data) == 0
test("S3c delete tag", s3c)

print("\n=== S4 — Toggle quote ===")
r = sb.table("quotes").select("id,active").eq("active", True).limit(1).execute()
def s4_pre(): assert len(r.data) > 0
test("S4a quote exists", s4_pre)
qid = r.data[0]["id"]
sb.table("quotes").update({"active": False}).eq("id", qid).execute()
r2 = sb.table("quotes").select("active").eq("id", qid).execute()
def s4b(): assert r2.data[0]["active"] == False
test("S4b deactivate", s4b)
sb.table("quotes").update({"active": True}).eq("id", qid).execute()
r3 = sb.table("quotes").select("active").eq("id", qid).execute()
def s4c(): assert r3.data[0]["active"] == True
test("S4c reactivate", s4c)

print("\n=== S5 — Carga manual ===")
QA_TEXT = "S5 test quote " + str(int(time.time()))
r1 = http_post("/admin/quotes/manual", {"text": QA_TEXT, "author": "S5 Author", "tags": ["life"]})
def s5a(): assert r1.status_code == 201
test("S5a POST 201", s5a)
sb.table("quotes").delete().eq("author", "S5 Author").execute()
r2 = sb.table("quotes").select("*").eq("author", "S5 Author").execute()
def s5b(): assert len(r2.data) == 0
test("S5b cleanup", s5b)

print(f"\n{'='*40}")
print("Streamlit backend QA complete")
print(f"{'='*40}")
