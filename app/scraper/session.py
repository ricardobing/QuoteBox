"""Manejo de sesión HTTP autenticada para quotes.toscrape.com."""

from __future__ import annotations

import logging
from typing import Final

import requests
from bs4 import BeautifulSoup

from app.config import Settings

logger = logging.getLogger(__name__)

LOGIN_PATH: Final[str] = "/login"


class ScraperAuthError(RuntimeError):
    """Error de autenticación contra el sitio de scraping."""


def build_http_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "QuoteBoxBot/1.0 (+https://quotebox.local)"})
    return session


def login_with_csrf(session: requests.Session, settings: Settings) -> None:
    login_url = f"{settings.scrape_base_url}{LOGIN_PATH}"

    try:
        page_response = session.get(login_url, timeout=20)
        page_response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError("No se pudo obtener la página de login.") from exc

    try:
        soup = BeautifulSoup(page_response.text, "html.parser")
        csrf_input = soup.find("input", {"name": "csrf_token"})
        csrf_token = (csrf_input.get("value") if csrf_input else None) or ""
        if not csrf_token:
            raise ValueError("csrf_token no encontrado en login form.")
    except Exception as exc:
        raise RuntimeError("No se pudo extraer csrf_token desde login.") from exc

    payload = {
        "username": settings.scrape_username,
        "password": settings.scrape_password,
        "csrf_token": csrf_token,
    }

    try:
        auth_response = session.post(login_url, data=payload, timeout=20)
        auth_response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError("Fallo HTTP durante POST de login.") from exc

    if "Logout" not in auth_response.text:
        raise ScraperAuthError(
            "Autenticación fallida: no se detectó sesión activa tras login. "
            "Verificá SCRAPE_USERNAME y SCRAPE_PASSWORD."
        )

    logger.info("Login exitoso en %s", settings.scrape_base_url)
