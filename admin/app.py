"""Panel administrativo Streamlit para QuoteBox.

Este archivo define el esqueleto base del panel:
- CRUD de tags monitoreados
- Trigger manual de scraping
- Vista de frases con toggle active/inactive

La lógica de integración se implementará en la siguiente etapa.
"""

from __future__ import annotations

import os

import requests
import streamlit as st


def get_api_base_url() -> str:
    """Retorna URL base de FastAPI desde variables de entorno."""
    return os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")


def render_header() -> None:
    """Renderiza cabecera principal del panel."""
    st.set_page_config(page_title="QuoteBox Admin", page_icon="💬", layout="wide")
    st.title("QuoteBox Admin")
    st.caption("Gestión de tags, frases y disparo manual de scraping")


def render_tags_section(api_base_url: str) -> None:
    """Renderiza sección CRUD de monitored_tags (placeholder)."""
    st.subheader("Tags monitoreados")
    st.info("Sección placeholder: aquí se mostrará el CRUD de tags.")
    _ = api_base_url


def render_scrape_trigger_section(api_base_url: str) -> None:
    """Renderiza botón de trigger manual contra FastAPI."""
    st.subheader("Scraping")
    if st.button("Correr scraping ahora", type="primary"):
        try:
            response = requests.post(f"{api_base_url}/trigger/scrape", timeout=20)
            if response.ok:
                st.success("Trigger enviado correctamente.")
            else:
                st.error(f"Error enviando trigger: {response.status_code}")
        except requests.RequestException as exc:
            st.error(f"No se pudo conectar con FastAPI: {exc}")


def render_quotes_section(api_base_url: str) -> None:
    """Renderiza vista de frases con toggle active/inactive (placeholder)."""
    st.subheader("Frases")
    st.info("Sección placeholder: aquí se mostrará listado de frases con toggles de estado.")
    _ = api_base_url


def main() -> None:
    """Punto de entrada del panel Streamlit."""
    api_base_url = get_api_base_url()
    render_header()
    st.write(f"API base URL: {api_base_url}")

    col1, col2 = st.columns([1, 1])
    with col1:
        render_tags_section(api_base_url)
    with col2:
        render_scrape_trigger_section(api_base_url)

    st.divider()
    render_quotes_section(api_base_url)


if __name__ == "__main__":
    main()
