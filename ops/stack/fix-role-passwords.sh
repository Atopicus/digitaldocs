#!/usr/bin/env bash
# Tras el PRIMER arranque: POSTGRES_PASSWORD no se propaga a los roles internos.
# Se fuerza con ALTER USER, como supabase_admin por TCP a 127.0.0.1.
# La contraseña se lee dentro del contenedor; no se imprime ni pasa por el host.
set -euo pipefail
docker exec -i digitaldocs-db sh -c '
  PGPASSWORD="$POSTGRES_PASSWORD" psql -q -v ON_ERROR_STOP=1 -h 127.0.0.1 -U supabase_admin -d postgres -v pw="$POSTGRES_PASSWORD"
' <<'SQL'
alter user supabase_auth_admin    with password :'pw';
alter user supabase_storage_admin with password :'pw';
alter user authenticator          with password :'pw';
SQL
echo "Contraseñas de los roles internos fijadas."
