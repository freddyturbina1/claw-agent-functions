#!/usr/bin/env python3
"""
Autentica se.urquiza@gmail.com con scope calendar.readonly
y guarda el token en ~/.gcalcli/token_gmail.json
"""

import json
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CLIENT_SECRET = os.path.expanduser('~/.gcalcli/client_secret.json')
TOKEN_PATH = os.path.expanduser('~/.gcalcli/token_gmail.json')

def main():
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
            creds = flow.run_local_server(
                port=0,
                login_hint='se.urquiza@gmail.com',
                prompt='consent'
            )

        with open(TOKEN_PATH, 'w') as f:
            f.write(creds.to_json())
        print(f"✅ Token guardado en {TOKEN_PATH}")
        print(f"   Scopes: {creds.scopes}")
    else:
        print("✅ Token ya válido")

if __name__ == '__main__':
    main()
