#!/bin/bash
# Wrapper para gcalcli con credenciales de Seba
# Las credenciales OAuth se cargan desde variables de entorno
export PATH="$PATH:/Users/seba/Library/Python/3.9/bin"
gcalcli \
  --client-id "${GCALCLI_CLIENT_ID}" \
  --client-secret "${GCALCLI_CLIENT_SECRET}" \
  --config-folder ~/.gcalcli \
  "$@" 2>&1 | grep -Ev "(FutureWarning|warn\(|warnings\.warn|NotOpenSSL|site-packages|python version)"
