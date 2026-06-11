"""Servicios para administrar tags monitoreados."""

from __future__ import annotations

from typing import Any

from supabase import Client


def list_monitored_tags(supabase: Client, only_active: bool = False) -> list[dict[str, Any]]:
    query = supabase.table("monitored_tags").select("*").order("tag")
    if only_active:
        query = query.eq("active", True)
    result = query.execute()
    return result.data or []


def get_active_tags(supabase: Client) -> set[str]:
    result = supabase.table("monitored_tags").select("tag").eq("active", True).execute()
    if not result.data:
        return set()
    return {row.get("tag", "").lower() for row in result.data}


def create_monitored_tag(supabase: Client, tag: str, active: bool = True) -> dict[str, Any]:
    result = (
        supabase.table("monitored_tags")
        .insert({"tag": tag.strip().lower(), "active": active})
        .execute()
    )
    return (result.data[0] if result.data else {})


def update_monitored_tag(supabase: Client, tag_id: str, *, tag: str | None = None, active: bool | None = None) -> None:
    payload: dict[str, Any] = {}
    if tag is not None:
        payload["tag"] = tag.strip().lower()
    if active is not None:
        payload["active"] = active
    if not payload:
        return
    supabase.table("monitored_tags").update(payload).eq("id", tag_id).execute()


def delete_monitored_tag(supabase: Client, tag_id: str) -> None:
    supabase.table("monitored_tags").delete().eq("id", tag_id).execute()
