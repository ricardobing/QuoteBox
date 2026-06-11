"""QuoteBox Admin — Panel operativo Streamlit."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import requests
import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

st.set_page_config(page_title="QuoteBox Admin", page_icon="", layout="wide")

BACKEND_URL = st.secrets.get("BACKEND_URL", os.getenv("BACKEND_URL", os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")))


def get_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
    key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
    if not url or not key:
        st.error("SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY son requeridos en secrets.")
        st.stop()
    return create_client(url, key)


def require_auth() -> None:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return

    admin_password = st.secrets.get("ADMIN_PASSWORD", os.getenv("ADMIN_PASSWORD", "admin123"))

    st.title("QuoteBox Admin")
    password = st.text_input("Contrasena", type="password")
    if st.button("Ingresar"):
        if password == admin_password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Contrasena incorrecta.")
    st.stop()


def render_metrics(supabase: Client) -> None:
    active = supabase.table("quotes").select("id", count="exact").eq("active", True).execute()
    tags = supabase.table("monitored_tags").select("id", count="exact").eq("active", True).execute()
    pending = (
        supabase.table("unknown_author_requests")
        .select("id", count="exact")
        .eq("escalated", False)
        .execute()
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Frases activas", active.count or 0)
    col2.metric("Tags monitoreados", tags.count or 0)
    col3.metric("Pendientes escalacion", pending.count or 0)


def render_scrape_trigger() -> None:
    st.subheader("Scraping manual")
    if st.button("Correr scraping ahora", type="primary"):
        with st.spinner("Ejecutando scraping..."):
            try:
                resp = requests.post(f"{BACKEND_URL}/trigger/scrape", timeout=120)
                if resp.ok:
                    data = resp.json()
                    st.success(
                        f"Scraping completado: {data.get('pages_scraped', 0)} paginas, "
                        f"{data.get('quotes_found', 0)} quotes encontradas, "
                        f"{data.get('quotes_new', 0)} nuevas."
                    )
                else:
                    st.error(f"Error: {resp.status_code} - {resp.text}")
            except requests.RequestException as exc:
                st.error(f"No se pudo conectar al backend: {exc}")


def render_scrape_runs(supabase: Client) -> None:
    st.subheader("Ultimas corridas de scraping")
    result = (
        supabase.table("scrape_runs")
        .select("*")
        .order("started_at", desc=True)
        .limit(5)
        .execute()
    )
    if result.data:
        rows = []
        for run in result.data:
            started = run.get("started_at", "")
            if started:
                started = started[:19].replace("T", " ")
            rows.append({
                "Inicio": started,
                "Estado": run.get("status", ""),
                "Paginas": run.get("pages_scraped", 0),
                "Encontradas": run.get("quotes_found", 0),
                "Nuevas": run.get("quotes_new", 0),
            })
        st.dataframe(rows, use_container_width=True)
    else:
        st.info("No hay corridas registradas.")


def main() -> None:
    require_auth()
    supabase = get_supabase()

    st.title("QuoteBox Admin")
    st.caption("Gestion de frases, tags y scraping")

    render_metrics(supabase)
    st.divider()
    render_scrape_trigger()
    st.divider()
    render_scrape_runs(supabase)


if __name__ == "__main__":
    main()
