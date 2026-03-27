#!/usr/bin/env python3
"""
Autentica con Whoop API via OAuth2
Guarda el token en ~/.whoop/token.json
"""

import json
import os
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests

CLIENT_ID = "543cb8d6-1016-41f7-bfad-424ee45ed995"
CLIENT_SECRET = "59a7229a0980f8fb80f8cb5e012399c17f63143844213feb24b8d3b7148f993c"
REDIRECT_URI = "http://localhost:8765/callback"
AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
TOKEN_PATH = os.path.expanduser("~/.whoop/token.json")
SCOPES = "read:profile read:body_measurement read:cycles read:recovery read:sleep read:workout offline"

auth_code = None

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Autenticado correctamente. Puedes cerrar esta ventana.</h2></body></html>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Error: no se recibi\xf3 c\xf3digo.")

    def log_message(self, format, *args):
        pass  # silenciar logs

def main():
    os.makedirs(os.path.expanduser("~/.whoop"), exist_ok=True)

    # Construir URL de autorización
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "state": "claw_whoop_auth"
    }
    url = AUTH_URL + "?" + urllib.parse.urlencode(params)

    print("Abriendo navegador para autorizar Whoop...")
    webbrowser.open(url)

    # Esperar callback
    server = HTTPServer(("localhost", 8765), CallbackHandler)
    print("Esperando autorización en http://localhost:8765/callback ...")
    server.handle_request()

    if not auth_code:
        print("❌ No se recibió código de autorización.")
        return

    # Intercambiar código por token
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })

    if resp.status_code != 200:
        print(f"❌ Error obteniendo token: {resp.status_code} {resp.text}")
        return

    import time
    token = resp.json()
    # Calcular expires_at absoluto para que el refresh automático sepa cuándo actuar
    if "expires_in" in token and "expires_at" not in token:
        token["expires_at"] = int(time.time()) + token["expires_in"]

    with open(TOKEN_PATH, "w") as f:
        json.dump(token, f, indent=2)

    print(f"✅ Token guardado en {TOKEN_PATH}")
    print(f"   Scopes: {token.get('scope', '?')}")

if __name__ == "__main__":
    main()
