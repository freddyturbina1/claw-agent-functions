#!/usr/bin/env python3
"""
Autentica sebastian.urquiza@pandago.eco con scope calendar.readonly
y guarda el token en ~/.gcalcli/token_work.json
"""

import json
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CLIENT_SECRET = os.path.expanduser('~/.gcalcli/client_secret.json')
TOKEN_PATH = os.path.expanduser('~/.gcalcli/token_work.json')

def main():
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
            # login_hint sugiere la cuenta de empresa en el navegador
            creds = flow.run_local_server(
                port=0,
                login_hint='sebastian.urquiza@pandago.eco',
                prompt='consent'
            )

        with open(TOKEN_PATH, 'w') as f:
            f.write(creds.to_json())
        print(f"✅ Token guardado en {TOKEN_PATH}")
        print(f"   Scopes: {creds.scopes}")
        print(f"   Cuenta: sebastian.urquiza@pandago.eco")
    else:
        print("✅ Token ya válido, no se necesita reautenticar")

if __name__ == '__main__':
    main()
