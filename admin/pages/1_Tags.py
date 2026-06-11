"""Gestion de tags monitoreados."""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

st.set_page_config(page_title="Tags — QuoteBox Admin", page_icon="")


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


def fetch_tags(supabase: Client):
    return supabase.table("monitored_tags").select("*").order("tag").execute().data or []


def main() -> None:
    require_auth()
    supabase = get_supabase()

    st.title("Tags monitoreados")

    st.subheader("Agregar tag")
    with st.form("add_tag_form", clear_on_submit=True):
        new_tag = st.text_input("Nombre del tag")
        submitted = st.form_submit_button("Agregar")
        if submitted and new_tag.strip():
            try:
                supabase.table("monitored_tags").insert({
                    "tag": new_tag.strip().lower(),
                    "active": True,
                }).execute()
                st.success(f"Tag '{new_tag.strip().lower()}' agregado.")
                st.rerun()
            except Exception as exc:
                st.error(f"Error al agregar tag: {exc}")

    st.divider()

    tags = fetch_tags(supabase)
    if not tags:
        st.info("No hay tags configurados.")
        return

    for tag in tags:
        col1, col2, col3 = st.columns([3, 1, 1])
        col1.write(f"**{tag['tag']}**")
        active = col2.checkbox("Activo", value=tag.get("active", True), key=f"active_{tag['id']}")
        if active != tag.get("active", True):
            supabase.table("monitored_tags").update({"active": active}).eq("id", tag["id"]).execute()
            st.rerun()
        if col3.button("Eliminar", key=f"del_{tag['id']}"):
            supabase.table("monitored_tags").delete().eq("id", tag["id"]).execute()
            st.rerun()


if __name__ == "__main__":
    main()
