#!/usr/bin/env python3
"""Test rápido de la API de Whoop"""

import json, os, sys
import requests

# Añadir el directorio de scripts al path para importar whoop_auth
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from whoop_auth import get_whoop_headers

BASE_URL = "https://api.prod.whoop.com/developer"

try:
    headers = get_whoop_headers()
except RuntimeError as e:
    print(f"❌ {e}")
    sys.exit(1)

# Perfil
r = requests.get(f"{BASE_URL}/v2/user/profile/basic", headers=headers)
print("👤 Perfil:", r.json())

# Último ciclo (para obtener cycle_id actual)
r = requests.get(f"{BASE_URL}/v2/cycle", headers=headers, params={"limit": 1})
cycles = r.json()
print("\n🔄 Último ciclo:", json.dumps(cycles, indent=2))

if cycles.get("records"):
    cycle_id = cycles["records"][0]["id"]

    # Recovery del ciclo actual
    r = requests.get(f"{BASE_URL}/v2/cycle/{cycle_id}/recovery", headers=headers)
    print("\n💚 Recovery:", json.dumps(r.json(), indent=2))

    # Sleep del ciclo actual
    r = requests.get(f"{BASE_URL}/v2/cycle/{cycle_id}/sleep", headers=headers)
    print("\n😴 Sleep:", json.dumps(r.json(), indent=2))

# Últimos workouts
r = requests.get(f"{BASE_URL}/v2/activity/workout", headers=headers, params={"limit": 3})
workouts = r.json()
print("\n🏃 Últimos workouts:", json.dumps(workouts, indent=2))
