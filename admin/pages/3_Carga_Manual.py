"""Carga manual de frases."""

from __future__ import annotations

import os

import requests
import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

st.set_page_config(page_title="Carga Manual — QuoteBox Admin", page_icon="")

BACKEND_URL = st.secrets.get("BACKEND_URL", os.getenv("BACKEND_URL", os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")))


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


def render_manual_form() -> None:
    st.subheader("Nueva frase")

    with st.form("manual_quote_form", clear_on_submit=True):
        text = st.text_area(
            "Frase",
            max_chars=500,
            placeholder="Escribe la frase...",
            height=100,
        )
        st.caption(f"{len(text)}/500")

        author = st.text_input("Autor", placeholder="John Lennon")

        tags_raw = st.text_input("Tags", placeholder="love, humor, life")

        submitted = st.form_submit_button("Cargar frase", type="primary")

        if submitted:
            if not text.strip():
                st.error("La frase es obligatoria.")
                return
            if not author.strip():
                st.error("El autor es obligatorio.")
                return

            tags = [t.strip().lower() for t in tags_raw.split(",") if t.strip()]

            payload = {
                "text": text.strip(),
                "author": author.strip(),
                "tags": tags,
                "source": "manual",
            }

            try:
                resp = requests.post(
                    f"{BACKEND_URL}/admin/quotes/manual",
                    json=payload,
                    timeout=15,
                )
                if resp.status_code == 201:
                    st.success("Frase cargada correctamente.")
                elif resp.status_code == 409:
                    st.warning("Esta frase ya existe en el storage.")
                else:
                    detail = resp.json().get("detail", resp.text)
                    st.error(f"Error: {detail}")
            except requests.RequestException as exc:
                st.error(f"No se pudo conectar al backend: {exc}")


def render_manual_quotes_table(supabase: Client) -> None:
    st.divider()
    st.subheader("Frases cargadas manualmente")

    result = (
        supabase.table("quotes")
        .select("*")
        .eq("source", "manual")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    if not result.data:
        st.info("No hay frases cargadas manualmente.")
        return

    for q in result.data:
        col1, col2, col3, col4 = st.columns([3, 2, 1.5, 0.7])
        text = q.get("text", "")
        truncated = text[:80] + "..." if len(text) > 80 else text
        col1.write(truncated)
        col2.write(f"**{q.get('author', '')}**")
        tags = ", ".join(q.get("tags", [])[:3])
        col3.write(tags)
        active = q.get("active", True)
        label = "Activo" if active else "Inactivo"
        col4.write(f":{'green' if active else 'red'}[{label}]")
        st.divider()


def main() -> None:
    require_auth()
    supabase = get_supabase()

    st.title("Carga Manual de Frases")

    render_manual_form()
    render_manual_quotes_table(supabase)


if __name__ == "__main__":
    main()
