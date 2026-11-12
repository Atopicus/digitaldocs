# Plan de fases — digitaldocs

Una fase a la vez. Ninguna empieza sin que la anterior haya pasado su criterio de
aceptación y Joan lo haya confirmado explícitamente.

El orden no es arbitrario: cada fase se apoya en algo ya verificado de la anterior. El
frontend no empieza hasta que el esquema y sus tests de seguridad están en verde, y las
pantallas de documentos no empiezan hasta que el processor extrae de punta a punta.

**Última actualización:** 12/11/2026

| Fase | Qué | Estado |
|---|---|---|
| 0 | Repo y documentos | ✅ |
| 1 | Stack backend en pie | ✅ |
| 2 | DNS, TLS y enrutado | ✅ |
| 3 | Esquema y tests | pendiente |
| 4 | Autenticación y primer despliegue | pendiente |
| 5 | Processor: firma y almacenamiento | pendiente |
| 6 | Processor: extracción | pendiente |
| 7 | Configuración de IA, subida y cola | pendiente |
| 8 | Listado, detalle y revisión | pendiente |
| 9 | Exportación a Excel | pendiente |
| 10 | Backup y recuperación | pendiente |
| 11 | Versión 1.0.0 | pendiente |

En cada fase, «Joan hace» son los pasos de infraestructura que Claude no toca
(`CLAUDE.md` §1.8). Claude da los valores exactos y espera la confirmación.

---

## Fase 0 — Repo y documentos ✅

`CLAUDE.md`, `docs/fases.md`, `docs/decisiones.md` y `docs/diseno.md`. Nada de código.

**Aceptación:** existen los cuatro ficheros y nada más; ningún secreto.

---

## Fase 1 — Stack backend en pie ✅

`~/supabase-digitaldocs/` con Postgres 15, GoTrue y PostgREST, mismas imágenes que
nosdiners. Contenedores `digitaldocs-db`, `digitaldocs-auth`, `digitaldocs-rest`; red
`digitaldocs_internal` más `proxy-net`; datos en `~/supabase-digitaldocs/data/db`.
El compose se versiona en el repo (`ops/stack/docker-compose.yml`, solo `${VAR}`) y se
copia al directorio del stack. `GOTRUE_SITE_URL` apunta a
`https://digitaldocs.joansalas.com` desde el principio, con `GOTRUE_MAILER_AUTOCONFIRM`
en `true` hasta la Fase 4b.

Incluye el `ALTER USER` de los roles internos tras el primer arranque y las cadenas de
conexión con nombre de contenedor cualificado.

**Joan hace:** crear `~/supabase-digitaldocs/.env` con el script que Claude entrega (genera
los secretos sin imprimirlos) y arrancar el stack, o autorizar a Claude a arrancarlo.

**Aceptación**
- Tres contenedores arriba, `db` healthy, migraciones de GoTrue aplicadas, PostgREST
  conectado.
- El único puerto publicado es `127.0.0.1:5433`.
- `docker ps` de los contenedores de nosdiners y ClarityFin, idéntico antes y después.

**Validado el 12/11/2026:** tres contenedores arriba, `db` healthy, 44 migraciones de
GoTrue aplicadas, `auth.users` y `auth.uid()` existen, PostgREST conectado con el esquema
cargado; `/health` de GoTrue y la raíz de PostgREST devuelven 200 desde la red interna;
único puerto nuevo en el host, `127.0.0.1:5433`; los otros 14 contenedores, idénticos
antes y después. El `ALTER USER` de los roles internos se hizo con
`ops/stack/fix-role-passwords.sh`. Ficheros: `ops/stack/` (compose, `init-env.py`,
`install.sh`, `fix-role-passwords.sh`).

---

## Fase 2 — DNS, TLS y enrutado ✅

**Joan hace:** registro A de `api-digitaldocs.joansalas.com`; Proxy Host en NPM con
Let's Encrypt (Force SSL, HTTP/2, HSTS sin subdominios); Custom Locations `/auth/v1` →
`digitaldocs-auth:9999` y `/rest/v1` → `digitaldocs-rest:3000`, cada una con su `rewrite`
y su bloque de CORS. Claude entrega el texto exacto de cada campo al empezar la fase. La
location `/processor` se añade en la Fase 5, cuando el contenedor exista.

**Aceptación**
- `/auth/v1/health` y `/rest/v1/` devuelven 200 por HTTPS.
- HTTP redirige con 301.
- El `.conf` del proxy host existe de verdad en NPM; no basta con que la interfaz diga
  «online».

**Validado el 12/11/2026, desde fuera:** `/auth/v1/health` y `/rest/v1/` devuelven 200 por
HTTPS (HTTP/2); HTTP redirige con 301; HSTS presente y sin subdominios; certificado de
Let's Encrypt válido hasta el 10/02/2027; el preflight de las dos locations responde 204
con el origen fijo al frontend; el `rewrite` recorta el prefijo (PostgREST busca
`public.<tabla>`, GoTrue responde en `/health`). `api-nosdiners` sigue respondiendo 200.
Los bloques exactos y los tropiezos están en `docs/decisiones.md`, «Proxy host y Custom
Locations de NPM».

---

## Fase 3 — Esquema y tests

`db/migrations/0001_init.sql`: `profiles`, `documents`, `document_pages`, `ai_settings`,
el trigger de alta de perfil, RLS, permisos cerrados desde el nacimiento (defaults de
`supabase_admin` y `postgres` incluidos), las RPC de `authenticated`, el rol
`processor_service` con sus funciones `processor_*`, la función única de columnas
derivadas y la conversión de importe en texto a céntimos. Esquema en `docs/decisiones.md`.

Tests en `tests/` (`node:test` + `pg`, cada uno en transacción con `ROLLBACK`).

**Joan hace:** aprobar el SQL tras el dry-run; fijar la contraseña de `processor_service`
con `\password`; generar el par de claves de cifrado con el comando que Claude entrega.

**Aceptación**
- `0001_init.sql` aplicada tras dry-run y aprobación.
- Dos usuarios no se ven entre sí en ninguna tabla (RLS real con
  `SET LOCAL ROLE authenticated` y claims).
- Leer la columna de la clave como `authenticated` da `42501`, no una fila vacía. La clave
  guardada no está en claro en la tabla.
- Guardián en verde: ninguna función abierta a `PUBLIC` ni a `anon`; `authenticated`
  ejecuta exactamente la lista blanca; `authenticated` no escribe nada fuera de la lista
  blanca; todo lo de `public` es de `supabase_admin`.
- `processor_service` ejecuta exactamente sus funciones y no lee ninguna tabla.
- Transiciones de estado: las válidas pasan, las inválidas fallan con error fijado.
- El sexto documento activo de un usuario se rechaza.
- Conversión de importes: `"1.234,56"` → 123456; vacío, texto o formato dudoso → `NULL`.
- `frontend/src/types/database.ts` generado desde el esquema, con la versión del CLI fijada.

---

## Fase 4 — Autenticación y primer despliegue

### 4a — Frontend

Esqueleto del frontend (Vite, Tailwind, shadcn/ui, i18n, tokens de `docs/diseno.md`),
registro con nombre, login, logout, sesión persistente, ruta protegida y perfil mínimo.
Proxy de Vite para desarrollo. Despliegue en Vercel para verificar ya en el dominio real.

**Joan hace:** proyecto de Vercel desde `github.com/Atopicus/digitaldocs` (Root Directory
`frontend`), dominio `digitaldocs.joansalas.com` y las variables de entorno que Claude
indique.

### 4b — Correo real

Confirmación obligatoria por Resend y recuperación de contraseña («he olvidado la
contraseña»: pedir el correo y fijar la nueva al volver del enlace).

**Joan hace:** subdominio remitente `mail.digitaldocs.joansalas.com` con SPF, DKIM y DMARC
en Resend; `RESEND_API_KEY` en `.env`; Claude entrega el cambio de compose
(`GOTRUE_MAILER_AUTOCONFIRM: "false"`, SMTP, asuntos y plantillas).

**Aceptación**
- Registro, login, logout y sesión persistente desde `digitaldocs.joansalas.com`, en
  ventana privada.
- El JWT contiene `role: authenticated` y `aud: authenticated`; una petición autenticada a
  `/rest/v1/profiles` devuelve 200.
- El perfil se crea solo al registrarse.
- Ningún literal en JSX: todos los textos salen de i18n.
- Un registro nuevo no obtiene sesión hasta confirmar el correo; los tres registros DNS
  verificados en Resend.
- Recuperar la contraseña funciona de punta a punta.

---

## Fase 5 — Processor: firma y almacenamiento

`ops/processor/`: servicio Node con `Dockerfile` y `docker-compose.yml`, contenedor
`digitaldocs-processor`, secretos en `~/supabase-digitaldocs/secrets/processor.env`.
Validación del JWT, URLs firmadas de subida y descarga, y borrado de documento. Se fijan
aquí los límites de tamaño por página y de páginas por documento.

**Joan hace:** bucket privado `digitaldocs` en R2; token de API limitado a ese bucket;
regla CORS del bucket (origen `https://digitaldocs.joansalas.com`, métodos `PUT` y `GET`);
Custom Location `/processor` en NPM; rellenar `processor.env` con la plantilla que Claude
entrega.

**Aceptación**
- Tests del JWT: caducado, firma alterada, algoritmo `none`, `aud` o `role` erróneos, sin
  cabecera. Todos rechazados.
- Un usuario que pide URLs de un documento ajeno recibe el mismo error que si no existiera.
- Test del generador de claves: nunca produce ni acepta una clave con prefijo de otro
  usuario.
- Subida y descarga reales con URL firmada; el objeto queda bajo el prefijo del usuario.
- Una URL firmada deja de servir al caducar; un `GET` sin firma al bucket falla.
- Una subida con tamaño o tipo distinto del firmado es rechazada por R2.
- Borrar un documento deja su prefijo vacío en R2 y la fila borrada.

---

## Fase 6 — Processor: extracción

Trabajador de cola, adaptadores de OpenAI, Gemini y Anthropic, prompt y validación de
totales portados de la referencia, errores tipados y reencolado al arrancar. Catálogo de
modelos de cada proveedor verificado contra su endpoint de modelos y fechado en
`docs/decisiones.md`; parámetros de transporte ajustados por proveedor.

**Joan hace:** una clave de prueba por proveedor que quiera verificar, cargada desde la
interfaz o por la RPC, nunca pegada en el chat.

**Aceptación**
- El prompt es idéntico, carácter a carácter, al de la referencia (test que lo compara).
- La validación de totales da el mismo resultado que la de la referencia sobre un juego de
  casos fijo: cuadra, descuadre de subtotal, descuadre de línea, campos vacíos.
- Una factura real se extrae de punta a punta con cada proveedor del que haya clave.
- Un descuadre forzado marca `needs_review`.
- Sin clave guardada, el documento acaba en `error` con `no_api_key`.
- Una clave inválida acaba en `provider_auth`; una respuesta que no es JSON, en
  `invalid_response`.
- Reiniciar el contenedor a media extracción devuelve el documento a la cola.
- Los logs de una extracción completa no contienen la clave ni datos del documento.

---

## Fase 7 — Configuración de IA, subida y cola

Pantalla de configuración de IA (proveedor, modelo, clave). Subida multipágina de JPG, PNG
y PDF con tipo de documento obligatorio; el PDF se convierte a imágenes en el navegador.
Indicador de cola que lee el estado de la BD.

**Aceptación**
- Guardar proveedor, modelo y clave; al recargar, la interfaz indica que hay clave sin
  mostrarla.
- La clave no aparece en ninguna respuesta de red del navegador.
- Subida de un JPG, un PNG y un PDF de varias páginas; se pueden añadir y quitar páginas
  antes de enviar.
- Sin tipo de documento no se puede enviar.
- La cola sobrevive a recargar la página y a cerrar la pestaña.
- El sexto documento activo se rechaza con un mensaje claro.

---

## Fase 8 — Listado, detalle y revisión

Panel con las cuatro cifras de la referencia (documentos, total, pendientes de revisión,
último procesado) y tabla con búsqueda, orden y paginación en servidor. Detalle con las
imágenes y los datos lado a lado, edición de campos y de líneas, marca de «requiere
revisión», reintento de un documento en error y borrado.

**Aceptación**
- La búsqueda y la paginación se resuelven en la consulta, no en memoria.
- Editar un campo o una línea se guarda y actualiza las columnas derivadas (número, fechas,
  total).
- La marca de revisión se puede poner y quitar.
- Las imágenes se cargan con URL firmada; la URL de un usuario no sirve para otro.
- Borrar un documento lo quita de la lista y vacía sus objetos en R2.
- Un importe ilegible se muestra como «—», nunca como 0,00.
- Verificado en móvil y escritorio.

---

## Fase 9 — Exportación a Excel

Exportación del documento con las tres hojas de la referencia: General, Líneas y Totales.

**Aceptación**
- El libro abre en Excel y LibreOffice.
- Los importes llegan como números, no como texto; los vacíos llegan vacíos.
- El nombre del fichero sigue la pauta de la referencia (tipo y número de documento).

---

## Fase 10 — Backup y recuperación

Copia diaria de la BD (`pg_dump -Fc` y roles), rotación, restauración de prueba periódica
y `docs/recuperacion.md`. Incluye el par de claves de cifrado y `secrets/` en lo que hay
que conservar. R2 tiene su propia durabilidad; se documenta qué pasa si se pierde.

**Joan hace:** decidir el destino de la copia externa; instalar el cron.

**Aceptación**
- Una copia restaurada en una base vacía reproduce los mismos recuentos por tabla.
- `docs/recuperacion.md` cubre la BD rota y el VPS perdido, marcando lo no probado.

---

## Fase 11 — Versión 1.0.0

Versión, página de novedades, ayuda y repaso final de accesibilidad.

**Aceptación**
- `npm run build` y los tests del frontend y del processor en verde.
- Suite de BD completa en verde.
- Recorrido completo en ventana privada: registro, configuración de IA, subida, cola,
  revisión, exportación y borrado.

---

## Deuda técnica

- **Los tests de BD corren contra la base de producción (decidido el 12/11/2026).** Misma
  situación que nosdiners: una sola base en loopback 5433, cada test en transacción con
  `ROLLBACK`. Riesgos: una migración pendiente probada dentro de un test toma locks sobre
  objetos que la app usa en vivo (mitigado con `lock_timeout = '2s'`); un helper que hiciera
  `COMMIT` tocaría datos reales. Aquí pesa más que en nosdiners porque el registro es
  abierto y la base guarda claves de IA de terceros. **Revisar antes de que haya usuarios
  ajenos con datos reales:** un contenedor de tests aparte, con las mismas migraciones.
- **No hay registro de migraciones aplicadas.** Como en nosdiners, se compara la fecha del
  dump con el `git log` de `db/migrations`.

---

## Fuera de la v1

Descarga del documento en JSON (la referencia la tiene; no está en el alcance pedido),
eliminar la cuenta desde el perfil (hoy dejaría objetos huérfanos en R2: cuando se haga,
pasa por el processor), más idiomas, tema claro, detección de duplicados, historial de
cambios, filtros avanzados, exportación de varios documentos a la vez, PDF nativo enviado
al proveedor sin convertir, y una clave de IA global o un proveedor «incluido».

Ninguno cambia el núcleo si se añade después. Por eso están fuera.
