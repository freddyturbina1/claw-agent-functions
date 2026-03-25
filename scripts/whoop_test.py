#!/usr/bin/env python3
"""Test rápido de la API de Whoop"""

import json, os, requests
from datetime import datetime, timedelta

TOKEN_PATH = os.path.expanduser("~/.whoop/token.json")
BASE_URL = "https://api.prod.whoop.com/developer/v1"

def get_headers():
    with open(TOKEN_PATH) as f:
        token = json.load(f)
    return {"Authorization": f"Bearer {token['access_token']}"}

headers = get_headers()

# Perfil
r = requests.get(f"{BASE_URL}/user/profile/basic", headers=headers)
profile = r.json()
print("👤 Perfil:", profile)

# Recuperación de hoy
r = requests.get(f"{BASE_URL}/recovery", headers=headers, params={"limit": 1})
recovery = r.json()
print("\n💚 Última recuperación:", json.dumps(recovery, indent=2))

# Último workout
r = requests.get(f"{BASE_URL}/workout", headers=headers, params={"limit": 3})
workouts = r.json()
print("\n🏃 Últimos workouts:", json.dumps(workouts, indent=2))
