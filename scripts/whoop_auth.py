#!/usr/bin/env python3
"""
Helper de autenticación Whoop con refresh automático.
Importar en cualquier script con: from whoop_auth import get_whoop_headers
"""

import json
import os
import time
import requests

CLIENT_ID = "543cb8d6-1016-41f7-bfad-424ee45ed995"
CLIENT_SECRET = "59a7229a0980f8fb80f8cb5e012399c17f63143844213feb24b8d3b7148f993c"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
TOKEN_PATH = os.path.expanduser("~/.whoop/token.json")


def _load_token():
    if not os.path.exists(TOKEN_PATH):
        raise RuntimeError(f"Token no encontrado en {TOKEN_PATH}. Ejecuta auth_whoop.py primero.")
    with open(TOKEN_PATH) as f:
        token = json.load(f)
    # Detectar si el archivo contiene un error en lugar de un token válido
    if "error" in token or "access_token" not in token:
        raise RuntimeError(
            f"Token inválido o corrompido en {TOKEN_PATH}. "
            "Ejecuta auth_whoop.py para re-autenticar."
        )
    return token


def _save_token(token: dict):
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        json.dump(token, f, indent=2)


def _is_expired(token: dict, margin_seconds: int = 300) -> bool:
    """Devuelve True si el token expira en menos de margin_seconds."""
    expires_at = token.get("expires_at")
    if expires_at is None:
        return False  # No sabemos cuándo expira, asumir válido
    return time.time() >= (expires_at - margin_seconds)


def _refresh_token(token: dict) -> dict:
    """Refresca el access_token usando el refresh_token."""
    refresh_token = token.get("refresh_token")
    if not refresh_token:
        raise RuntimeError(
            "No hay refresh_token disponible. "
            "Ejecuta auth_whoop.py para re-autenticar con scope 'offline'."
        )

    print("🔄 Refrescando token de Whoop...")
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })

    if resp.status_code != 200:
        raise RuntimeError(
            f"Error al refrescar token: {resp.status_code} {resp.text}. "
            "Ejecuta auth_whoop.py para re-autenticar."
        )

    new_token = resp.json()

    # Calcular expires_at si la API devuelve expires_in
    if "expires_in" in new_token and "expires_at" not in new_token:
        new_token["expires_at"] = int(time.time()) + new_token["expires_in"]

    # Conservar refresh_token anterior si la API no devuelve uno nuevo
    if "refresh_token" not in new_token and refresh_token:
        new_token["refresh_token"] = refresh_token

    _save_token(new_token)
    print("✅ Token refrescado y guardado.")
    return new_token


def get_valid_token() -> dict:
    """
    Carga el token, lo refresca si está próximo a expirar.
    Devuelve el token actualizado.
    """
    token = _load_token()
    if _is_expired(token):
        token = _refresh_token(token)
    return token


def get_whoop_headers() -> dict:
    """
    Devuelve los headers Authorization listos para usar en requests.
    Refresca el token automáticamente si es necesario.
    """
    token = get_valid_token()
    return {"Authorization": f"Bearer {token['access_token']}"}
