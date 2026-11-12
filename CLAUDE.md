# digitaldocs — reglas del proyecto

Procesamiento inteligente de documentos comerciales (facturas, albaranes, pedidos): el
usuario sube las páginas, un modelo de IA extrae los datos, el usuario los revisa, los
corrige y los exporta a Excel. Cada usuario trabaja solo con sus datos y con su propia
clave de IA.

Lee este fichero entero al empezar cada sesión. Si algo aquí contradice una instrucción
del chat, **pregunta antes de actuar**.

Sigue la arquitectura y el método de nosdiners (`~/dev/nosdiners`, solo lectura). Lo que
cambia respecto a nosdiners está escrito aquí y razonado en `docs/decisiones.md`.

---

## 1. Reglas que no se negocian

1. **Una migración aplicada no se edita.** Cualquier cambio de esquema va en una migración
   nueva (`000N_...sql`) y requiere aprobación explícita de Joan antes de escribirla.
   Mientras `0001_init.sql` no esté aplicada se puede revisar; después, nunca.

2. **El prompt de extracción y la validación de totales no se cambian sin aprobación.**
   Vienen de la app de referencia (`~/dev/graficondigital-ref`,
   `supabase/functions/process-document/index.ts`) y se portan tal cual: mismo texto, mismas
   reglas, mismas tolerancias (0,05 y 0,10). Si un test falla, el fallo está en la
   implementación, nunca en el valor esperado. **Para y pregunta.** Ajustar un valor
   esperado para que un test pase es el peor error posible en este proyecto.

3. **Importes.** El JSON extraído se guarda como lo devuelve el modelo: cadenas en formato
   español, vacías si no eran legibles. Lo único que se deriva a columna es el total del
   documento, en céntimos (`total_cents bigint`), `NULL` si no se puede leer. Nunca `float`
   ni `numeric` con decimales en una columna, y nunca un importe ilegible convertido en 0.
   La conversión de cadena a céntimos se hace por texto, sin pasar por `float`.

4. **Ningún secreto en el repo.** Ni en código, ni en tests, ni en ejemplos con valores
   reales. Viven en `~/supabase-digitaldocs/.env` y `~/supabase-digitaldocs/secrets/`
   (`chmod 600`, fuera de git). `docker-compose.yml` los referencia como `${VAR}`. Si
   necesitas uno, pídelo: **no leas ni imprimas ficheros `.env` ni nada de `secrets/`.**

5. **La clave de IA del usuario nunca vuelve al navegador ni aparece en un log.** Se
   escribe por RPC, se guarda cifrada, la columna no es legible por `authenticated` y el
   frontend solo sabe si hay clave guardada. Ni el processor ni los tests la imprimen, ni
   siquiera recortada. Tampoco se registra el contenido de un documento.

6. **RLS activo en todas las tablas, sin excepciones temporales.** Cada usuario ve y
   gestiona solo sus datos. Si una política te bloquea, se arregla la política.

7. **El servidor nunca firma una ruta ajena.** Las claves de objeto de R2 las genera el
   servidor con el id del usuario como prefijo. El navegador solo envía ids de documento;
   el processor resuelve las claves desde la BD filtrando por el usuario del JWT y, además,
   rechaza cualquier clave cuyo prefijo no sea ese usuario. Al borrar un documento se
   borran sus objetos.

8. **No toques la infraestructura sin aprobación.** DNS, Nginx Proxy Manager, `ufw`, el
   proyecto de Vercel, el bucket y el token de R2 y su regla CORS los hace Joan: cuando una
   fase lo necesite, dale los valores exactos y espera a que confirme.
   **No toques nada de nosdiners, de ClarityFin ni de sus contenedores** (`supabase-nosdiners-*`,
   `nosdiners-telegram-bot`, `supabase-min-*`, `nginx-proxy-manager-app-1`). Nunca
   `docker compose down -v` fuera de `~/supabase-digitaldocs/`.

   **Excepción documentada** a «ningún contenedor publica puertos al host»: el servicio `db`
   publica `127.0.0.1:5433:5432`, solo loopback, para migraciones, tests y generación de
   tipos. El 5432 es de nosdiners.

9. **Una fase a la vez.** No empieces la siguiente sin que Joan confirme que la anterior ha
   pasado su criterio de aceptación (`docs/fases.md`).

10. **Solo la v1.** El alcance es el de la app de referencia. El modelo y la estructura
    quedan preparados para crecer, pero no se construye nada que no esté en la v1.

---

## 2. Modelo de datos — lo esencial

| Tabla | Qué guarda |
|---|---|
| `profiles` | Un perfil por usuario, creado por el trigger `on_auth_user_created`. |
| `documents` | Un documento: tipo, estado de proceso, datos vigentes (`data`), respuesta original del modelo (`extracted_data`), columnas derivadas y marca de revisión. |
| `document_pages` | Una fila por página, con su clave de objeto en R2. |
| `ai_settings` | Proveedor, modelo y clave de IA cifrada de cada usuario. |

- **Estados de un documento:** `uploading` → `queued` → `processing` → `done` o `error`.
  La cola vive en la BD, no en el navegador. Máximo 5 documentos activos por usuario.
- **`data` y `extracted_data`:** `extracted_data` es lo que devolvió el modelo y solo lo
  escribe el processor; `data` es lo vigente y lo edita el usuario por RPC.
- **Columnas derivadas** (`document_number`, `document_date`, `due_date`, `total_cents`):
  las mantiene **una única función SQL**, la misma para el processor y para la edición. No
  hay dos caminos de escritura.
- **El JSON conserva las claves en castellano** del prompt (`proveedor`, `lineas`,
  `totales`). Tablas, columnas y valores de enumerado van en inglés. La correspondencia
  entre ambos vive en un único módulo.

### Permisos

- `anon` no tiene nada en `public`.
- `authenticated` **solo lee** (con RLS). Toda escritura pasa por una RPC `security definer`
  dedicada, salvo `profiles.display_name`. `ai_settings` tiene `SELECT` por columna, sin la
  columna de la clave: el frontend nunca puede hacer `select *` sobre esa tabla.
- `processor_service` es un rol de login sin acceso a tablas: solo `EXECUTE` en las
  funciones `processor_*`.
- RLS decide qué **filas** ves; `GRANT`/`REVOKE` por columna decide qué **campos** tocas.
  Un `REVOKE` de columna no hace nada mientras exista el privilegio de tabla: se revoca el
  de tabla y se concede por columna, y toda columna nueva se añade al `GRANT`.

---

## 3. Stack

| | |
|---|---|
| Frontend | React + Vite + TypeScript |
| UI | Tailwind + shadcn/ui |
| Tablas | TanStack Table (colapsan a tarjetas en móvil) |
| Datos | `supabase-js` contra PostgREST + GoTrue self-hosted |
| Backend | Postgres 15 + GoTrue + PostgREST en `~/supabase-digitaldocs/` |
| Processor | Servicio Node en contenedor (`ops/processor`): valida el JWT, firma URLs de R2 y ejecuta la extracción |
| Ficheros | Cloudflare R2, bucket privado `digitaldocs`, URLs firmadas de corta duración |
| IA | OpenAI, Google Gemini o Anthropic, con la clave de cada usuario. Sin clave global |
| API | `https://api-digitaldocs.joansalas.com` (`/auth/v1`, `/rest/v1`, `/processor/v1`) |
| Frontend desplegado | `https://digitaldocs.joansalas.com`, Vercel desde `github.com/Atopicus/digitaldocs` |
| Correo | Resend, remitente `no-reply@mail.digitaldocs.joansalas.com` |

Contenedores `digitaldocs-db`, `digitaldocs-auth`, `digitaldocs-rest` y
`digitaldocs-processor`; red `digitaldocs_internal` más `proxy-net`.

**Sin Kong, sin Edge Functions, sin Supabase Storage.** El enrutado y el recorte de
prefijos los hace Nginx Proxy Manager. Lo que en Supabase Cloud sería una Edge Function,
aquí es una función de Postgres o el processor.

---

## 4. Convenciones de código

- TypeScript estricto en el frontend. Nada de `any` para salir del paso.
- Tipos de base de datos **generados** desde el esquema real, con la versión del CLI
  fijada. No inventes campos: si no está en una migración, no existe.
- Nombres en inglés en el código (tablas, variables, tipos). Las claves del JSON extraído
  son la excepción (ver §2).
- Interfaz **solo en castellano**, pero con i18n desde el primer componente: **nunca**
  literales incrustados en JSX. Añadir un idioma después debe ser añadir un fichero.
- Moneda, idioma y formato son configuración, no constantes. Los importes se muestran con
  la moneda del documento (`documents.currency`), nunca con un «€» fijo.
- Responsive equilibrado: un solo árbol de componentes, sin rutas separadas para móvil.
- El processor es JavaScript (`.mjs`) con `node:test`, como `ops/telegram-bot` de
  nosdiners. Llama a los proveedores con `fetch`, sin SDK.

---

## 5. Flujo de trabajo

1. Antes de escribir código, di **qué** vas a hacer y **qué ficheros** vas a tocar. Espera
   confirmación.
2. Cambios pequeños y verificables. Después de cada uno, di cómo comprobarlo.
3. Si algo no cuadra con la especificación, **para y pregunta**. No improvises una
   interpretación razonable.
4. No instales dependencias nuevas sin justificarlas antes.
5. No hagas `git push` ni apliques migraciones sin que Joan lo pida.
6. **Dry-run antes de aplicar.** Una migración no se aplica ni se commitea sin validación
   de Joan: primero se ejecuta en `BEGIN ... ROLLBACK` y se le enseña el SQL.
7. **Suite de BD en rojo = no se aplica ninguna migración.** Se para y se reporta.
   - **Modifica objetos existentes** → suite de BD completa (`npm run test:db`), una vez,
     con la versión final de la migración.
   - **Solo añade objetos nuevos** → test propio de la migración + `permissions-hygiene` +
     los tests de listas de permisos que la afecten (p. ej. el del rol del processor).
   - En caso de duda, se trata como el primero.
8. **Los tests de BD corren contra la base de producción** (decisión de Joan, deuda anotada
   en `docs/fases.md`). Por eso: cada test en una transacción con `ROLLBACK`, ningún helper
   hace `COMMIT`, `lock_timeout` de 2 s para las migraciones pendientes, y ningún test lee
   ni imprime la columna de la clave de IA de filas que ya existían.
9. **Antes de un `git push` que toque `frontend/`: build y tests del frontend en verde.**
   Lo mismo para `ops/processor/` con sus tests.
10. **Cadenas de comandos con build, tests, commit o push se cortan ante el primer error**:
    `set -e` o `&&` de verdad, sin `;` ni pipes a `grep`/`tail` que enmascaren el código de
    salida (si hay que filtrar, `set -o pipefail`).

---

## 6. Contexto heredado

Este proyecto sustituye a una app generada con Lovable (`github.com/Atopicus/graficondigital`,
clonada en `~/dev/graficondigital-ref`, solo lectura). Es la **especificación funcional**:
pantallas, flujo y, sobre todo, el prompt y la validación de totales. No se copia su
estructura de código ni sus dependencias, no se migra ningún dato y no se despliega.

**nosdiners y ClarityFin siguen en marcha en el mismo VPS**: no toques nada suyo.

Trampas ya conocidas de este stack (heredadas de nosdiners). No las redescubras:

- `POSTGRES_PASSWORD` no se propaga a `supabase_auth_admin`, `supabase_storage_admin` ni
  `authenticator`. Hay que forzarlo tras el primer arranque con `ALTER USER`, conectando
  como `supabase_admin` por TCP a `127.0.0.1`.
- GoTrue necesita `GOTRUE_JWT_AUD` y `GOTRUE_JWT_DEFAULT_GROUP_NAME` en `authenticated`,
  aunque los logs los marquen como deprecados. Sin ellos los usuarios se crean con
  `role = ''` y toda petición autenticada devuelve 400.
- En `proxy-net` los alias son un espacio de nombres compartido. Las cadenas de conexión
  usan siempre el nombre cualificado del contenedor (`digitaldocs-db`), nunca `db`.
- En las Custom Locations de NPM: solo un `rewrite`, nunca un `proxy_pass` manual.
- GoTrue devuelve `Access-Control-Allow-Origin` fijo a `GOTRUE_SITE_URL`, no refleja el
  `Origin`. Un solo origen válido; en desarrollo, proxy de Vite.
- Las funciones nuevas nacen con `EXECUTE` para `PUBLIC`, y los defaults de
  `supabase_admin` conceden de más a `anon` y `authenticated` sobre tablas nuevas. Aquí se
  cierran en `0001_init.sql` y los vigila el guardián.
- Las migraciones se aplican siempre como `supabase_admin`: todo lo de `public` es suyo.
- Sin `vercel.json` con el rewrite de SPA, recargar una ruta que no sea `/` da 404.
- Depura el frontend desplegado **siempre en ventana privada**.

---

## 7. Dirección de diseño

La dirección visual vive en `docs/diseno.md`: tokens, escala tipográfica, presentación de
importes y de estados, densidad y suelo de accesibilidad. Léelo antes de escribir cualquier
componente. No inventes colores ni tamaños que no estén ahí.

---

## 8. Convenciones de SQL y permisos

1. **Funciones nuevas en `public` o `app`:** `revoke all ... from public, anon`;
   `grant execute` a `authenticated` (solo si es RPC o helper de RLS), a
   `processor_service` (solo las `processor_*`), a `service_role` y a `postgres`; y alta en
   la lista blanca del guardián (`tests/seguridad/permissions-hygiene.test.ts`). Las tablas
   nuevas van también a su lista blanca de escrituras.
2. **RPC de escritura:** `security definer` con `search_path = public, pg_temp`,
   comprobación explícita de `auth.uid()` y de propiedad, y el mismo error genérico para lo
   ajeno y lo inexistente.
3. **Funciones `processor_*`:** `security definer`, reciben el id del usuario como
   parámetro explícito y filtran por él; nunca devuelven filas de otro usuario.
4. **Vistas:** siempre con `security_invoker = true`.
5. **Vistas de solo lectura nuevas:** antes de proponerlas, comprueba si el dato ya está en
   algo que el frontend carga y justifica por qué no basta derivarlo en el cliente.
6. **Redefinir una función existente (`create or replace`):** parte siempre de su
   definición actual en la BD (`pg_get_functiondef`), no de la migración donde se creó. Si
   cambia la firma, `drop` + `create`: un `create or replace` deja la firma vieja viva.

---

## 9. Versión, novedades y ayuda

Todo cambio visible para el usuario incluye:

1. **Subir la versión** en `frontend/package.json` (funcionalidad nueva → minor, arreglo →
   patch). Una subida por despliegue. La versión de salida es **1.0.0**; hasta entonces, 0.x.
2. **Una entrada en Novedades** (`frontend/src/content/changelog.ts`), en lenguaje de
   usuario y en 2–3 líneas.
3. **Actualizar la sección de ayuda afectada** si cambia cómo se usa algo.

En el resumen final de la tarea, incluye siempre la versión nueva y el texto de Novedades.
