# Dirección visual — digitaldocs

Este documento fija el aspecto de la aplicación. Es la referencia para cualquier
componente nuevo: si algo no está aquí, se decide antes de escribirlo, no sobre la marcha.

Origen: el sistema visual de nosdiners (`~/dev/nosdiners/docs/diseno.md`, dirección
«Panel»), heredado por decisión del 12/11/2026. Se conservan los tokens, la tipografía, la
densidad y el suelo de accesibilidad. Cambian los papeles de color, porque aquí no hay
gasto ni ingreso: hay documentos, estados de proceso y datos que revisar. Las secciones de
nosdiners sobre presupuestos, bote, ámbitos y secciones de categoría no aplican y no están.

---

## 1. Principio

Los datos mandan. Esta es una aplicación para **comprobar que lo extraído coincide con el
documento** y corregirlo deprisa. La imagen original y los datos son los protagonistas;
cromo, iconos y decoración se quedan en segundo plano.

Corolario práctico: ante la duda entre añadir un adorno o quitar ruido, se quita ruido.

Segundo corolario, propio de este proyecto: **la interfaz nunca aparenta más certeza que
el modelo.** Un campo vacío se ve vacío, un total ilegible no se pinta como cero, y lo que
necesita revisión se señala sin alarmar.

---

## 2. Color

Tema oscuro azulado. Los tokens se definen como variables CSS en `:root` y **nunca** se
escriben valores sueltos en un componente.

```css
:root {
  /* superficies */
  --ground:      #121A22;  /* fondo de página */
  --surface:     #1A242E;  /* tarjetas y paneles */
  --surface-alt: #26313D;  /* pistas de barra, formularios en línea, etiqueta neutra */
  --border:      #2B3846;  /* divisor de fila dentro de una tarjeta */

  /* elevación de tarjeta: distinta de --border para que ambos se distingan */
  --card-border: rgba(255, 255, 255, 0.35);
  --card-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);

  /* texto */
  --text:        #E9EEF3;  /* cuerpo y cifras */
  --text-dim:    #93A3B2;  /* etiquetas, fechas, contexto */
  --text-soft:   #C6D2DD;  /* texto de botón secundario */

  /* acentos */
  --accent:      #E7B24B;  /* ámbar: acción principal y «requiere revisión» */
  --accent-soft: #F3D08A;  /* ámbar claro: fondo suave de un aviso de revisión */
  --data:        #62AEE8;  /* azul: proceso en curso, progreso, enlaces */
  --data-deep:   #3B6E96;  /* azul profundo: pista de progreso ya recorrida */

  /* error */
  --error:       #FF7A7A;  /* rojo: SOLO el estado de error (ver abajo) */

  /* filas de total y subtotal de las tablas compactas (§12) */
  --row-total-bg:    #2A3745;
  --row-subtotal-bg: #1D2833;
}
```

**Reparto de papeles**, que es lo que evita que la interfaz se vuelva un arcoíris:

| Token | Para qué | Nunca para |
|---|---|---|
| `--accent` | Botón principal, marca «requiere revisión», campo que no cuadra | Fondos de página, bordes decorativos, tipo de documento |
| `--data` | Documento en cola o procesándose, barra de progreso, enlaces | Botones de acción, documento ya terminado |
| `--text-dim` | Solo contexto: fecha, etiqueta de campo, contador, nota | El valor de un dato, y jamás el dato clave |
| `--error` | Documento en estado `error`, error de un formulario | Revisión pendiente, importes, borrar, cualquier adorno |

- **Lo bueno no se pinta.** Un documento terminado y sin revisión pendiente no lleva color
  ni insignia de éxito: es el estado normal. No hay verde en la interfaz.
- **Revisión no es error.** «Requiere revisión» es ámbar: pide atención, no anuncia un
  fallo. `--error` queda para lo que de verdad ha fallado. Nunca se usan los dos para lo
  mismo.
- **El tipo de documento no tiene color.** Factura, albarán, pedido y otro se distinguen
  por su texto, en una etiqueta neutra (§11). La referencia les daba un color a cada uno;
  aquí ese canal está reservado al estado.
- `--error` cumple AA sobre los fondos oscuros (6,95:1 sobre `--ground`, 6,23:1 sobre
  `--surface`, 5,23:1 sobre `--surface-alt`, medidos en nosdiners para este mismo valor).
- **El color nunca es la única señal.** Todo estado lleva además texto o icono con
  `aria-label`.

**Tema claro:** los tokens están nombrados por función, no por color, así que añadir un
tema claro más adelante es reescribir el bloque `:root`, no tocar componentes. No se
construye en la v1.

---

## 3. Tipografía

Una sola familia: **Archivo** (Google Fonts), variable en anchura y peso.

```
Archivo:wdth,wght@85..112,400;85..112,500;85..112,600;85..112,700
```

Las cifras grandes van ligeramente condensadas (`font-stretch: 95%`); la marca,
ligeramente expandida (`112%`).

### Escala

| Nivel | Tamaño | Peso | Color | Uso |
|---|---|---|---|---|
| Métrica | 42px / 40px móvil | 700 | `--text` | La cifra grande de una tarjeta del panel. Una por tarjeta. |
| Marca | 20px / 18px móvil | 700 | `--text` | «digitaldocs» |
| Título de sección | 17px / 15px móvil | 600 | `--text` | «Proveedor», «Líneas», «Totales» |
| Importe en lista | 16px | 600 | `--text` | Columna de total |
| Cuerpo | 15px | 400 | `--text` | Valor de un campo, navegación, etiquetas de botón |
| Contexto | 13px | 400 | `--text-dim` | Etiqueta de campo, fecha, subtítulo de métrica |
| Pie de dato | 12px | 400 | `--text-dim` | Número de página, contador, nota |

No se usan mayúsculas para etiquetas. Frase normal, mayúscula solo al principio.

---

## 4. Importes y datos extraídos

La regla más importante del documento.

- **Toda cifra lleva `font-variant-numeric: tabular-nums`**, alineada a la derecha en
  tablas. Sin excepción: importes, cantidades, precios y porcentajes.
- **Formato:** coma decimal, punto de millar también en cifras de cuatro dígitos, símbolo
  detrás (`1.245,60 €`). La moneda sale de `documents.currency`, nunca se asume en el
  código.
- **Sin signo ni color.** Un total de documento no es un gasto ni un ingreso: va en
  `--text`. Solo un importe negativo que venga así del documento lleva el signo menos
  tipográfico (`−`, U+2212).
- **Vacío es vacío.** Un importe o un campo que el modelo dejó en blanco se muestra como
  «—» en `--text-dim`, nunca como `0,00` ni como cadena vacía que colapse la fila. El
  total del panel suma solo los documentos con total legible y lo dice si alguno falta.
- **Lo extraído se muestra como está.** Precios unitarios con más de dos decimales,
  cantidades decimales y códigos de artículo se pintan tal cual vienen. No se redondea ni
  se reformatea lo que el usuario tiene que cotejar con la imagen.
- **Códigos y números de documento** en la misma familia, con `tabular-nums`; no se añade
  una tipografía monoespaciada.
- **Un dato que no cuadra** (la validación de totales marcó el documento) se señala en el
  propio campo o fila con un borde izquierdo de 3 px en `--accent` y un texto que dice qué
  no cuadra. Nunca solo con color.

---

## 5. Layout y densidad

- **Espaciado en múltiplos de 4**, con 20 y 24 px como respiraciones habituales dentro de
  tarjeta y 40 px de margen de página en escritorio (20 px en móvil).
- **Radio:** 12px en tarjetas, 8px en botones y controles, 6px en botones pequeños dentro
  de tarjeta, 4px en barras de progreso.
- **Tarjetas:** fondo `--surface`, borde `--card-border` de 1px y sombra `--card-shadow`.
  Las filas *dentro* de una tarjeta se separan con divisores `--border`, un color distinto
  a propósito.
- **Rejilla del panel:** cuatro métricas en escritorio, dos por fila en tableta, una
  tarjeta que las funde en móvil.
- **Móvil no es escritorio encogido.** Las tablas pasan a filas de dos líneas; el detalle
  apila imagen y datos (§13). Nunca scroll horizontal de página.
- **La acción principal en móvil vive en la cabecera** (`sticky top-0`), junto al menú:
  «Subir documento» siempre visible.

### Objetivos táctiles

Mínimo 44px de alto en cualquier control. La acción principal en móvil, 52px. Excepción:
dentro de las tablas compactas (§12) el menú «⋯» mide 32 px en escritorio.

---

## 6. Estados del documento

Un documento está siempre en uno de cinco estados. Cada uno tiene un texto y un
tratamiento fijos, iguales en la lista, en la cola y en el detalle.

| Estado | Texto | Tratamiento |
|---|---|---|
| `uploading` | Subiendo | `--data`, barra de progreso con las páginas subidas |
| `queued` | En cola | `--data`, icono de reloj, sin animación |
| `processing` | Analizando | `--data`, indicador de actividad |
| `done` | (ninguno) | Sin marca: es el estado normal |
| `error` | Error, con el motivo traducido | `--error`, icono de aviso y acción «Reintentar» |

- **«Requiere revisión» no es un estado**, es una marca sobre un documento `done`: etiqueta
  con icono y texto en `--accent`. Se puede poner y quitar a mano.
- El motivo de un error sale del código (`no_api_key`, `provider_auth`, …) traducido por
  i18n, con qué hacer a continuación. Nunca se muestra el texto crudo del proveedor.
- El único movimiento continuo permitido es el indicador de `processing`, y respeta
  `prefers-reduced-motion` (queda fijo, con el texto).
- Los cambios de estado se anuncian en una región `aria-live="polite"`.

---

## 7. Suelo de calidad

No negociable en ningún componente:

- `<button>`, `<a href>`, `<input>` + `<label>` reales. Nunca `onClick` sobre un `div`.
- `aria-label` en cualquier botón que solo lleve icono.
- Contraste mínimo 4.5:1 en texto, 3:1 a partir de 24px.
- Foco de teclado visible. No se elimina el `outline` sin sustituirlo.
- `prefers-reduced-motion` respetado.
- Iconos como SVG inline con trazo, heredando el color del texto. Nunca emoji.
- Toda imagen de página lleva `alt` con su número («Página 2 de 5»).
- La zona de subida es un `<button>` o un `<label>` de un `<input type="file">` real:
  arrastrar y soltar es un añadido, nunca la única forma.

---

## 8. Movimiento

Casi nada. Transiciones solo como respuesta a una acción de la persona: abrir, expandir,
confirmar. Nada de entradas escalonadas al cargar ni animaciones de hover en cada tarjeta.

Excepciones justificadas: el indicador de `processing` (§6) y el avance de la barra de
subida, porque muestran que algo está pasando.

---

## 9. Escritura de interfaz

- Frase normal, verbos activos, sin relleno.
- El botón dice lo que pasa: «Procesar documento», no «Enviar». La acción conserva el
  mismo nombre en todo el flujo.
- Los errores explican qué ha pasado y cómo arreglarlo. No piden perdón.
- Una pantalla vacía es una invitación a actuar («Sube tu primer documento»), no un cartel
  de «sin datos».
- Castellano vía i18n desde el primer componente. Ningún literal incrustado en JSX.
- Nombres fijos: «documento» (nunca «archivo» ni «fichero» para el conjunto), «página»
  (cada imagen), «requiere revisión», «configuración de IA», «clave de API».
- Sobre la clave de API se escribe con precisión: «Hay una clave guardada», nunca se
  insinúa que se pueda volver a ver.

---

## 10. Armazón de navegación

- **Escritorio:** barra lateral fija de 240px (`sticky top-0 h-dvh`), `bg-surface`, borde
  derecho. Marca arriba, las entradas de navegación debajo (Documentos, Subir,
  Configuración de IA), el indicador de cola, y Perfil + «Cerrar sesión» fijos al fondo.
- **Móvil:** cabecera `sticky top-0` con menú hamburguesa (abre el mismo menú en un panel
  lateral) y la acción principal siempre visible (§5).
- **Entrada activa:** nunca solo color. Peso de texto (`font-semibold`), borde izquierdo
  de 3px en `--text` y `aria-current="page"`.
- **Indicador de cola:** cuenta de documentos activos en una pastilla `--data`, visible
  solo si es mayor que 0. Al abrirlo lista cada documento con su estado (§6).
- **`h-dvh`, no `h-vh`**, en cualquier panel a pantalla completa.

---

## 11. Listas y filas

- **Fila dentro de una tarjeta:** divisor `--border` de 1px entre filas, nunca una caja
  individual. La caja con fondo `--surface-alt` se reserva para un formulario en línea.
- **Barra de estado:** 3px en el borde izquierdo de la fila, con el token del estado
  (`--data` activo, `--accent` requiere revisión, `--error` error, ninguna si está
  terminado). Refuerza lo que ya dice el texto; nunca es la única señal.
- **Etiqueta neutra** (tipo de documento, número de páginas): fondo `--surface-alt`, texto
  `--text`, borde `--border`, 11–12 px. Nunca ámbar, azul ni rojo.
- **Acciones de fila:** un único botón «⋯» con un menú, no botones sueltos. Orden: Ver,
  Exportar a Excel y, tras una línea de separación, Borrar. Una acción destructiva no
  cambia de color: la separa una línea fina y la confirma un diálogo.
- **Borrar pide confirmación** y dice que también se borran las imágenes.

---

## 12. Tablas compactas

Pauta para toda tabla de datos: la lista de documentos y las líneas de un documento.

- **Altura de fila:** la misma para todas las filas de una tabla. 36 px en escritorio;
  en móvil, filas de dos líneas (dato principal e importe arriba, contexto en pequeño
  debajo). Punto de corte en `md` (768 px).
- **Totales** con fondo propio: `--row-total-bg`, negrita. Las filas de datos no llevan
  fondo.
- **Importes y cantidades** a la derecha con `tabular-nums` y el **mismo borde derecho**
  en todas las filas: ninguna celda editable desplaza el borde con su padding.
- **Columnas secundarias se ocultan en móvil**, o la fila pasa a dos líneas. Nunca scroll
  horizontal de página. La tabla de líneas de un documento, que tiene trece columnas, es la
  única que puede desplazarse en horizontal dentro de su propio contenedor, con la
  descripción fija a la izquierda.
- **Marcas pequeñas** (revisión, tipo) viven dentro de la celda del dato principal, no en
  columnas propias.
- Las tablas son `<div role="table">` en CSS Grid con `role="row"` y `role="cell"`, con
  TanStack Table solo para el contenido de celda. Un `<table>` real vale para una tabla
  simple sin columnas que se ocultan.
- Búsqueda, orden y paginación se resuelven en servidor. Una columna que el servidor no
  puede ordenar no se ofrece como ordenable.

### Lista de documentos

Columnas: tipo y número (con las marcas), fecha, proveedor o cliente, total, estado, «⋯».
En móvil: número y total arriba; tipo, fecha y contacto debajo. Encima, una fila con el
buscador y, si hace falta, los filtros (§15).

---

## 13. Detalle y revisión

La pantalla donde se hace el trabajo: cotejar la imagen con los datos.

- **Escritorio:** dos columnas. A la izquierda, las páginas, con la activa a buen tamaño y
  miniaturas para cambiar; se queda fija (`sticky`) mientras se recorren los datos. A la
  derecha, los datos en secciones: General, Proveedor, Cliente, Líneas, Totales, Pago y
  observaciones.
- **Móvil:** apilado. Las páginas arriba, en un carrusel que se puede plegar; los datos
  debajo.
- **La imagen se puede ampliar** (zoom y abrir a pantalla completa). Es la fuente de
  verdad y tiene que poder leerse.
- **Edición en el sitio.** Cada campo es un `<input>` con su `<label>`; no hay un modo
  «ver» y otro «editar». Los cambios se guardan con un botón «Guardar cambios» que aparece
  cuando hay algo pendiente; salir con cambios sin guardar pide confirmación.
- **Líneas:** tabla compacta (§12) con añadir y quitar fila. Los totales no se recalculan
  solos al editar: lo que cuenta es lo que dice el documento. Si dejan de cuadrar, se
  señala (§4).
- **Cabecera del detalle:** tipo y número, la marca de revisión con su interruptor, y las
  acciones Exportar a Excel y Borrar.
- **Documento en `error`:** en lugar de los datos, el motivo y las acciones «Reintentar» y
  «Rellenar a mano». Las páginas siguen visibles.
- **Documento activo:** las páginas visibles y el estado (§6) donde irán los datos.

---

## 14. Subida

- **Orden fijo:** primero el tipo de documento (obligatorio), después las páginas.
- **Zona de subida** grande, con borde discontinuo `--border` y texto que dice los
  formatos (JPG, PNG, PDF) y el límite. Acepta arrastrar, pulsar y, en móvil, la cámara.
- **Páginas como miniaturas** numeradas, en rejilla, con quitar en cada una. El orden es
  el de la extracción y se ve.
- **Un PDF** se convierte en sus páginas y muestra el avance de la conversión.
- **El botón principal** está desactivado, con el motivo a la vista, mientras falte el
  tipo o no haya páginas. Con documentos ya activos dice «Añadir a la cola».
- **Sin clave de IA guardada**, la pantalla lo avisa antes de subir, con enlace a
  Configuración de IA. No se deja subir para fallar después.
- Al enviar, el formulario se vacía para el siguiente documento y el nuevo aparece en el
  indicador de cola.

---

## 15. Navegación y filtros

Dos controles distintos para dos preguntas distintas.

- **Pestañas (`NavTabs`)** cambian de vista dentro de una pantalla. Inactivas en
  `--text-dim` sin fondo; la activa con fondo `--accent` al 16 % y texto `--accent`.
  `role="tablist"`, la pestaña activa vive en la URL.
- **Control segmentado (`SegmentedControl`)** elige una opción entre 2 y 4 que filtra la
  misma vista. Cápsula `--surface` con borde `--border`; la activa en `--surface-alt`.
  Nunca ámbar. `role="radiogroup"`.
- **Barra de filtros de lista:** una fila con el buscador (`flex-1`) y los selects, sin
  etiquetas encima (cada control lleva `aria-label`). «Limpiar filtros» solo si hay alguno
  activo. En móvil, buscador más un botón «Filtros (n)» que despliega el resto.
- El ámbar sólido como fondo queda reservado al botón principal.

---

## 16. Configuración de IA

- Una pantalla, no un modal: proveedor, modelo y clave, en ese orden.
- **Proveedor:** control segmentado con los tres.
- **Modelo:** lista del proveedor elegido, con una línea de contexto por modelo en
  `--text-dim`. Sin insignias de colores para el coste.
- **Clave:** `<input type="password">` con `autocomplete="off"`. Si ya hay una guardada,
  el campo está vacío y un texto dice «Hay una clave guardada» con la fecha; escribir una
  nueva la sustituye, y hay una acción aparte para borrarla. **La clave guardada nunca se
  muestra, ni entera ni recortada.**
- Cambiar de proveedor avisa de que hará falta una clave nueva.
- Un texto breve explica que la clave es del usuario, que el coste de cada extracción lo
  factura su proveedor y que no hay clave compartida.
