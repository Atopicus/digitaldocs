#!/usr/bin/env bash
# Copia el compose versionado al directorio del stack. No arranca nada.
set -euo pipefail
STACK="$HOME/supabase-digitaldocs"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$STACK/secrets"
chmod 700 "$STACK" "$STACK/secrets"
cp "$HERE/docker-compose.yml" "$STACK/docker-compose.yml"
echo "Compose instalado en $STACK/docker-compose.yml"
