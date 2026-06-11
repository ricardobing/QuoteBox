"""Vista y gestion de frases."""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

st.set_page_config(page_title="Frases — QuoteBox Admin", page_icon="")

PAGE_SIZE = 20


def get_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
    key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
    if not url or not key:
        st.error("SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY requeridos en secrets.")
        st.stop()
    return create_client(url, key)


def require_auth() -> None:
    if not st.session_state.get("authenticated", False):
        st.warning("Ingresa la contrasena en la pagina principal.")
        st.stop()


def fetch_all_tags(supabase: Client) -> list[str]:
    result = supabase.table("monitored_tags").select("tag").execute()
    tags = set()
    if result.data:
        for row in result.data:
            tags.add(row.get("tag", "").lower())
    # Also get tags from quotes table
    q_result = supabase.table("quotes").select("tags").execute()
    if q_result.data:
        for row in q_result.data:
            for t in row.get("tags", []):
                tags.add(t.lower())
    return sorted(tags)


def main() -> None:
    require_auth()
    supabase = get_supabase()

    st.title("Frases")

    col1, col2, col3 = st.columns(3)
    with col1:
        author_filter = st.text_input("Filtrar por autor", key="author_filter")
    with col2:
        all_tags = fetch_all_tags(supabase)
        tag_filter = st.selectbox("Filtrar por tag", ["(todas)"] + all_tags, key="tag_filter")
    with col3:
        source_filter = st.selectbox("Origen", ["(todos)", "scraper", "manual"], key="source_filter")

    # Build query
    query = supabase.table("quotes").select("*", count="exact")

    if author_filter and author_filter.strip():
        query = query.ilike("author_slug", f"%{author_filter.strip().lower()}%")

    if source_filter != "(todos)":
        query = query.eq("source", source_filter)

    query = query.order("created_at", desc=True)

    result = query.execute()
    all_quotes = result.data or []

    # Filter by tag in Python (since Supabase array contains is complex)
    if tag_filter and tag_filter != "(todas)":
        all_quotes = [q for q in all_quotes if tag_filter in q.get("tags", [])]

    total = len(all_quotes)

    # Pagination
    page = st.number_input("Pagina", min_value=1, max_value=max(1, (total // PAGE_SIZE) + 1), value=1, key="page_num")
    start = (page - 1) * PAGE_SIZE
    page_quotes = all_quotes[start:start + PAGE_SIZE]

    st.caption(f"Mostrando {len(page_quotes)} de {total} frases")

    for q in page_quotes:
        col1, col2, col3, col4 = st.columns([4, 2, 1.5, 0.8])
        text = q.get("text", "")
        truncated = text[:80] + "..." if len(text) > 80 else text

        source_badge = ":green[manual]" if q.get("source") == "manual" else ":gray[scraper]"
        col1.write(f"_{truncated}_")
        col2.write(f"**{q.get('author', '')}**")
        col3.write(f"{', '.join(q.get('tags', [])[:3])}  {source_badge}")

        active = col4.checkbox("Activo", value=q.get("active", True), key=f"active_{q['id']}", label_visibility="collapsed")
        if active != q.get("active", True):
            supabase.table("quotes").update({"active": active}).eq("id", q["id"]).execute()
            st.rerun()

        st.divider()


if __name__ == "__main__":
    main()
