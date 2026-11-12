#!/usr/bin/env python3
"""Genera ~/supabase-digitaldocs/.env con secretos nuevos, sin imprimirlos.

No sobrescribe un .env existente. La contraseña de Postgres es hexadecimal
porque va dentro de URLs de conexión.
"""
import base64, hashlib, hmac, json, os, secrets, sys, time

path = os.path.expanduser("~/supabase-digitaldocs/.env")
if os.path.exists(path):
    sys.exit(f"Ya existe {path}: no se toca.")

def b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

def jwt(role: str, secret: str) -> str:
    now = int(time.time())
    head = b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = b64(json.dumps({"role": role, "iss": "digitaldocs", "iat": now,
                           "exp": now + 10 * 365 * 24 * 3600}, separators=(",", ":")).encode())
    sig = hmac.new(secret.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest()
    return f"{head}.{body}.{b64(sig)}"

jwt_secret = secrets.token_hex(32)
lines = [
    f"POSTGRES_PASSWORD={secrets.token_hex(24)}",
    f"JWT_SECRET={jwt_secret}",
    f"ANON_KEY={jwt('anon', jwt_secret)}",
    f"SERVICE_ROLE_KEY={jwt('service_role', jwt_secret)}",
    "RESEND_API_KEY=",
]
os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as f:
    f.write("\n".join(lines) + "\n")
print(f"Creado {path} (600) con: POSTGRES_PASSWORD, JWT_SECRET, ANON_KEY, SERVICE_ROLE_KEY, RESEND_API_KEY (vacía).")
