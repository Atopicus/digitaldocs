# Decisiones y trampas — digitaldocs

Memoria de por qué algo es como es, o de qué falló y cómo se reconoció. A diferencia de
`docs/fases.md`, esto no es un plan. Cada entrada nueva lleva fecha, dónde aplica, qué se
decidió, qué se descartó y por qué.

Las trampas del stack heredadas de nosdiners están en `CLAUDE.md` §6 y, con su historia
completa, en `~/dev/nosdiners/docs/decisiones.md`. No se repiten aquí.

---

## Punto de partida: arquitectura de nosdiners, funcionalidad de graficondigital

**Fecha:** 12/11/2026.

**Decidido:** digitaldocs se reconstruye desde cero con la arquitectura, las convenciones
de SQL y permisos y el flujo de trabajo de nosdiners. La app de Lovable
(`~/dev/graficondigital-ref`) es solo la especificación funcional. Se empieza sin datos: no
se migra nada de la app antigua.

**Lo que digitaldocs añade a nosdiners:** ficheros en Cloudflare R2 con URLs firmadas, y un
servicio Node (`ops/processor`) expuesto por HTTP que valida el JWT del usuario. El bot de
Telegram de nosdiners no escucha peticiones; el processor sí, y eso es nuevo.

**Lo que cambia respecto a nosdiners:** repositorio en GitHub (`Atopicus/digitaldocs`), no
en GitLab; interfaz solo en castellano; puerto de loopback 5433; el compose del stack se
versiona en el repo (`ops/stack/`), sin secretos.

---

## Importes: JSON literal y solo el total en céntimos

**Fecha:** 12/11/2026. **Dónde:** `documents.data`, `documents.total_cents`.

**El conflicto:** nosdiners exige importes en céntimos `bigint`. La extracción devuelve
cadenas en formato español (`"1.234,56"`), vacías cuando el dato no se lee, con precios
unitarios de más de dos decimales, cantidades decimales y porcentajes.

**Decidido:** el JSON se guarda como lo devuelve el modelo. Solo el total del documento se
deriva a `total_cents bigint`, y es `NULL` si no se puede leer. La conversión es por texto:
se quitan los puntos de millar, se exige el patrón entero con hasta dos decimales tras la
coma, y cualquier otra cosa da `NULL`. Sin `float` ni `numeric` en columnas.

**Descartado:** `numeric(12,2)` como la referencia (rompe la regla y, con su `|| 0`,
convierte un total ilegible en 0, que luego suma en «total facturado»); y normalizar todo
el JSON a céntimos (pierde los precios con más decimales y no distingue vacío de cero).

**Por qué:** el JSON es una transcripción de un documento, no un libro contable. La regla
del prompt es «mejor vacío que inventado», y la base de datos debe respetarla: vacío es
vacío. El total sí necesita columna para ordenar y sumar en servidor.

**La validación de totales usa `parseFloat`, y se queda así.** Es una comparación con
tolerancia para decidir si se marca revisión, no un importe que se guarde. Se porta tal
cual (`CLAUDE.md` §1.2).

---

## Nombres en inglés, JSON en castellano

**Fecha:** 12/11/2026.

**Decidido:** tablas, columnas y valores de enumerado en inglés (`doc_type`: `invoice`,
`delivery_note`, `order`, `other`). El JSON extraído conserva las claves del prompt
(`tipo_documento`, `proveedor`, `lineas`, `totales`), porque el prompt no se toca. La
correspondencia `factura` ↔ `invoice` y el acceso a las claves del JSON viven en un único
módulo por lado (processor y frontend), nunca repartidos por los componentes.

---

## Moneda: columna con valor por defecto, nunca un símbolo fijo

**Fecha:** 12/11/2026. **Dónde:** `documents.currency`.

**Decidido:** `currency char(3) not null default 'EUR'`. El frontend formatea con esa
columna. El prompt no extrae la moneda y no se le añade (no se toca); la columna existe
para que añadirla después no obligue a tocar componentes.

---

## La cola vive en la base de datos

**Fecha:** 12/11/2026. **Dónde:** `documents.status`, `processor_claim_next`.

**En la referencia:** la cola es un estado de React; se pierde al recargar, y la fila del
documento no existe hasta que la extracción termina.

**Decidido:** el documento se crea primero, con estado `uploading`, y recorre `queued`,
`processing` y `done` o `error`. El processor reclama el siguiente trabajo con
`FOR UPDATE SKIP LOCKED`, el endpoint responde 202 y el frontend consulta el estado
mientras haya documentos activos. Se conserva el límite de la referencia: 5 activos por
usuario, aplicado en `create_document`.

**Descartado:** mantener la petición HTTP abierta hasta que termine la extracción. Una
extracción tarda decenas de segundos y el proxy la cortaría.

**Por qué importa más adelante:** al arrancar, el processor devuelve a la cola lo que
quedó en `processing`. Un documento nunca se queda colgado por un reinicio.

---

## Un fallo de la IA es un error visible, no un documento vacío

**Fecha:** 12/11/2026.

**En la referencia:** si la extracción falla, se guarda un documento vacío marcado para
revisión y el motivo se pierde.

**Decidido:** estado `error` con un código tipado (`no_api_key`, `provider_auth`,
`rate_limited`, `invalid_response`, `provider_error`, `pages_missing`; lista cerrada en la
migración). El frontend traduce el código; el texto del proveedor no llega al usuario.
Acciones: reintentar o rellenar a mano.

---

## Bucket privado: el cliente envía ids, nunca URLs ni claves

**Fecha:** 12/11/2026. **Dónde:** `ops/processor`, `document_pages.object_key`.

**En la referencia:** bucket público, y la función descarga cualquier URL que el cliente
le mande en `imageUrls`.

**Decidido:** bucket privado `digitaldocs` en R2. La clave de cada objeto la genera el
servidor: `<user_id>/<document_id>/<page_id>.<ext>`. El navegador pide URLs firmadas por
id de documento; el processor obtiene las claves de una función que filtra por el usuario
del JWT y, como segunda barrera, rechaza cualquier clave cuyo prefijo no sea ese usuario.
Para extraer, el processor lee las páginas de R2 por la API S3, no por URL.

**Por qué:** aceptar una URL del cliente y descargarla desde el servidor es una puerta a
peticiones contra la red interna. Aceptar una clave del cliente obliga a validarla bien
siempre. Con ids no hay nada que validar salvo la propiedad, y eso lo hace la BD.

**Borrado:** `authenticated` no tiene `DELETE` sobre `documents`. El borrado pasa por el
processor, que borra primero los objetos y después la fila. Si falla a medias queda un
documento sin imágenes, visible y reintentable; al revés quedarían ficheros huérfanos de
un usuario que cree haberlos borrado.

---

## Clave de IA: cifrada con clave pública dentro de la RPC

**Fecha:** 12/11/2026. **Dónde:** `ai_settings`, `set_ai_settings`, `ops/processor`.

**Requisitos de Joan:** la clave se escribe por una RPC, la columna no es legible por
`authenticated` y el frontend solo sabe si hay clave guardada.

**Decidido:** además, se guarda cifrada. `set_ai_settings` cifra con `pgcrypto`
(`pgp_pub_encrypt`) usando una clave pública. La privada vive solo en
`~/supabase-digitaldocs/secrets/` y la usa el processor. `has_api_key` es una columna
generada. Cambiar de proveedor sin dar una clave nueva borra la anterior.

**Descartado:** guardarla en claro protegida solo por permisos. Los dumps y las copias
externas llevarían las claves de todos los usuarios, y un fallo en una función `definer`
las expondría todas.

**Descartado también:** cifrado simétrico dentro de la RPC, porque obligaría a tener la
clave maestra en la base de datos; y cifrar en el processor, porque Joan quiere que la
escritura sea una RPC.

**Pendiente para la Fase 3:** dónde se descifra. O en la BD, con una función `processor_*`
que recibe la privada como parámetro en cada llamada, o en Node. Lo primero garantiza
compatibilidad (pgcrypto con pgcrypto) a cambio de que la privada viaje por la red interna;
lo segundo exige una librería OpenPGP y comprobar que lee el formato de pgcrypto. Se decide
con una prueba, y también el tipo de clave que pgcrypto admite.

**No cubre:** quien tenga a la vez la base de datos y `secrets/` lo tiene todo. El cifrado
protege los dumps, las copias y las lecturas por SQL.

---

## Catálogo de modelos: se verifica en la Fase 6, no se fija ahora

**Fecha:** 12/11/2026.

**El problema:** los identificadores de la referencia están desfasados (`gpt-4o`,
`gemini-2.5-*-preview-*`, `claude-3-5-*`) y su proveedor «incluido» desaparece. La búsqueda
del 12/11/2026 en la documentación de OpenAI y de Google devolvió listas que se
contradicen entre páginas, así que no se fija ningún identificador de esos dos proveedores
desde aquí.

**Decidido:** tres proveedores (OpenAI, Google Gemini, Anthropic), sin clave global. El
catálogo se cierra en la Fase 6 consultando el endpoint de modelos de cada proveedor con
una clave real, se limita a modelos que aceptan imagen y se anota aquí con su fecha. Vive
en un único fichero versionado.

**Parámetros de la llamada.** La referencia envía `temperature: 0` y `max_tokens: 16384`.
Los modelos actuales pueden rechazar o renombrar esos parámetros. El prompt y la
validación no cambian; los parámetros de transporte se ajustan por proveedor en la Fase 6
y se anotan aquí.

---

## PDF: se convierte a imágenes en el navegador, como en la referencia

**Fecha:** 12/11/2026.

**Decidido:** el PDF se rasteriza en el navegador con pdf.js y se suben las imágenes; el
PDF original no se guarda. El worker de pdf.js se empaqueta con la app, no se carga de un
CDN como hace la referencia.

**Descartado para la v1:** enviar el PDF nativo al proveedor. Cambiaría la entrada del
modelo respecto a la referencia, cuyo prompt se reutiliza tal cual.

**Riesgo anotado:** un PNG a escala 3 puede superar el límite por imagen de algún
proveedor, y la referencia no lo controla. La Fase 5 fija un tamaño máximo por página, que
va firmado en la URL de subida; el navegador ajusta la escala y recomprime las fotos que lo
superen.

---

## Tests de BD contra producción

**Fecha:** 12/11/2026.

**Decidido por Joan:** como en nosdiners, una sola base y los tests contra ella, cada uno
en una transacción con `ROLLBACK`.

**Descartado:** un contenedor de tests aparte desde el primer día (era la recomendación de
Claude, por el registro abierto y las claves de IA de terceros).

**Condiciones que se derivan** (`CLAUDE.md` §5.8): ningún helper hace `COMMIT`;
`lock_timeout` de 2 s para las migraciones pendientes; ningún test lee ni imprime la
columna de la clave de filas existentes. Queda como deuda en `docs/fases.md`, a revisar
antes de que haya usuarios ajenos con datos reales.

---

## Correo: confirmación obligatoria por Resend

**Fecha:** 12/11/2026.

**Decidido:** registro abierto con confirmación de correo, remitente
`no-reply@mail.digitaldocs.joansalas.com`, subdominio propio con SPF, DKIM y DMARC. Se
arranca con autoconfirm (Fase 4a) y se activa en la 4b. Con correo disponible, la
recuperación de contraseña entra en la v1: con registro abierto, un usuario que olvida la
contraseña no tiene a quién pedírsela.

---

## Dirección visual: se hereda la de nosdiners

**Fecha:** 12/11/2026.

**Decidido:** mismo sistema que nosdiners (tema oscuro azulado, Archivo, tokens por
función, tablas compactas, suelo de accesibilidad), sin fase de propuestas. Cambian los
papeles de color: ámbar es acción principal y «requiere revisión», azul es proceso en
curso y enlaces, y aparece un rojo reservado al estado de error. Detalle en
`docs/diseno.md`.

**Descartado:** el tema claro azul de la referencia y una dirección propia elegida entre
dos maquetas.

---

## Alcance: qué entra de la referencia y qué no

**Fecha:** 12/11/2026.

**Entra:** registro y login, subida multipágina de JPG, PNG y PDF con tipo de documento,
cola en segundo plano, listado y detalle con revisión y edición, marca de «requiere
revisión», exportación a Excel y configuración de IA.

**Entra aunque no estaba en la lista:** recuperación de contraseña (ver «Correo»).

**No entra:** la descarga en JSON que tiene el detalle de la referencia. Está en
`docs/fases.md`, «Fuera de la v1».

**`extracted_data`:** única columna añadida pensando en crecer. Guarda la respuesta
original del modelo, que no se puede reconstruir después de que el usuario edite. Nada de
la v1 la muestra.

---

## Esquema aprobado en el plan

**Fecha:** 12/11/2026. Es la base de `0001_init.sql`; el SQL exacto se aprueba en la Fase 3.

- **`profiles`**: `id`, `display_name`, `locale` (solo `es`), `created_at`.
- **`documents`**: `id`, `user_id`, `doc_type`, `status`, `error_code`, `attempts`, `data`,
  `extracted_data`, `document_number`, `document_date`, `due_date`, `total_cents`,
  `currency`, `supplier_name` y `customer_name` (generadas desde `data`), `needs_review`,
  `ai_provider`, `ai_model`, `created_at`, `updated_at`, `processed_at`.
- **`document_pages`**: `id`, `document_id`, `user_id`, `page_number`, `object_key`,
  `content_type`, `size_bytes`.
- **`ai_settings`**: `user_id`, `provider`, `model`, la clave cifrada, `has_api_key`
  (generada), `updated_at`.
- **RPC de `authenticated`**: `create_document`, `submit_document`, `retry_document`,
  `update_document_data`, `set_needs_review`, `set_ai_settings`, `clear_ai_api_key`.
- **Funciones de `processor_service`**: `processor_upload_targets`,
  `processor_download_targets`, `processor_claim_next`, `processor_complete`,
  `processor_fail`, `processor_requeue_stale`, `processor_delete_document`.

**Endpoints del processor** (`/processor/v1`): `GET /health`,
`POST /documents/:id/upload-urls`, `POST /documents/:id/download-urls`,
`POST /documents/:id/process`, `DELETE /documents/:id`. JWT HS256 con el secreto del stack,
`aud` y `role` `authenticated`, algoritmo fijado. CORS fijo al origen del frontend.

---

## Proxy host y Custom Locations de NPM

**Fecha:** 12/11/2026. **Dónde:** Nginx Proxy Manager, proxy host de
`api-digitaldocs.joansalas.com` (lo configura Joan). nosdiners no tiene documentado el
texto de sus locations; aquí sí queda.

**Proxy host:** `http` → `digitaldocs-rest:3000`, Block Common Exploits, Force SSL,
HTTP/2, HSTS sin subdominios. La pestaña **Advanced** del proxy host queda vacía.

**Custom Locations.** El texto va en el engranaje de cada location, solo el bloque:

`/auth/v1` → `http`, `digitaldocs-auth`, `9999`:

```nginx
if ($request_method = OPTIONS) {
    add_header Access-Control-Allow-Origin "https://digitaldocs.joansalas.com" always;
    add_header Access-Control-Allow-Methods "GET, POST, PUT, PATCH, DELETE, OPTIONS" always;
    add_header Access-Control-Allow-Headers "authorization, apikey, content-type, x-client-info, x-supabase-api-version" always;
    add_header Access-Control-Max-Age 1728000 always;
    return 204;
}
rewrite ^/auth/v1/?(.*)$ /$1 break;
```

`/rest/v1` → `http`, `digitaldocs-rest`, `3000`: el mismo bloque, con
`Access-Control-Allow-Headers "authorization, apikey, content-type, prefer, range, x-client-info, x-supabase-api-version, accept-profile, content-profile"`
y `rewrite ^/rest/v1/?(.*)$ /$1 break;`.

**Diferencia con nosdiners:** el preflight responde con el origen fijo al frontend, no con
`*`. Las respuestas que no son preflight llevan el CORS que pone cada servicio.

**Tropiezos, para no repetirlos:**
- Pegar el bloque en la pestaña Advanced del proxy host da
  `"add_header" directive is not allowed here`: a nivel de servidor nginx no admite
  `add_header` dentro de un `if`. Dentro de una location sí.
- NPM enseña solo «Internal Error». La causa real está en
  `docker logs nginx-proxy-manager-app-1`, en la línea `nginx: [emerg]`.
- Cada guardado con «Request a new SSL Certificate» pide un certificado, aunque la
  configuración falle después. Cinco iguales en una semana agotan el cupo de Let's Encrypt
  (`too many certificates (5) already issued for this exact set of identifiers`). Tras el
  primero, se elige el certificado existente en el desplegable.
- Orden que funcionó: proxy host mínimo, después el certificado, después una location por
  guardado, verificando desde fuera entre uno y otro.

**Pendiente en la Fase 5:** la location `/processor`. No se puede crear antes: NPM no
carga la configuración si el contenedor de destino no existe.
