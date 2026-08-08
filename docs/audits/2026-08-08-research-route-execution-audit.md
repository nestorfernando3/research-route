# Auditoría de ejecuciones de Research Route Slim

Fecha: 2026-08-08  
Alcance: skill instalado, sesiones locales de Codex, proyectos Research Route bajo `~/Documents`, validador, pruebas y benchmark publicado.

## Dictamen

Research Route Slim aporta continuidad y consigue que los proyectos reabran decisiones importantes. Su CLI es sólido en integridad de archivos, concurrencia y transferencia mecánica. El principal riesgo aparece entre esa solidez técnica y la calidad intelectual que los agentes atribuyen al resultado: `validate` puede pasar mientras claims, fuentes, venue y estado autoral incumplen el contrato académico del skill.

El caso más grave es *Suicidal Empathy*. La primera ejecución declaró un artículo listo para depósito con solo tres tarjetas de fuente y una tarjeta agregada que todavía exigía cotejo primario. Una auditoría posterior reabrió el proyecto, dividió el manuscrito en dos artículos e invalidó explícitamente el estado anterior de “listo para envío”. El skill facilitó la corrección, pero la corrección llegó después de producir un paquete editorial y afirmaciones de cierre excesivas.

## Método y cobertura

1. Se comparó el paquete del repositorio con la instalación activa en `~/.local/share/research-route`; `SKILL.md` y `route.py` coinciden byte a byte.
2. Se buscaron invocaciones explícitas en sesiones JSONL de Codex y raíces con `ROUTE.md` o `HANDOFF.md` en los proyectos locales.
3. Se inspeccionaron PAIDEIA, *Suicidal Empathy*, el artículo sobre fascismo en América Latina y el portafolio de poder constituyente.
4. Se ejecutó `quick_validate.py`, `route.py validate`, el checkpoint `handoff` y la suite `unittest`.
5. Se contrastaron los artefactos reales con `SKILL.md`, las cuatro referencias normativas, la rúbrica y los resultados publicados.

La búsqueda no demuestra exhaustividad fuera de `~/Documents` y de los directorios de sesiones de Codex. Las conclusiones sobre activación implícita tienen confianza media porque Codex no registra una señal inequívoca de “skill considerada y descartada”.

## Inventario observado

| Proyecto | Estado estructural actual | Evidencia principal |
| --- | --- | --- |
| PAIDEIA | `validate` y `handoff` pasan | 29 tarjetas, 9 work items cerrados, paquete DOCX/PDF y tres copias paralelas de estado |
| *Suicidal Empathy* | `validate` y `handoff` pasan | 3 tarjetas de fuente, 25 work items, 1 abierto; el estado posterior invalida el primer paquete “listo” |
| Fascismo en América Latina | ambos checkpoints fallan | ciclo legado `refine`, snapshot incompatible y sección privada heredada |
| Poder constituyente | no es una raíz Research Route | tres papers sostenidos y solo un `HANDOFF.md` independiente |

## Hallazgos

### P0. El andamiaje de producción contamina algunos manuscritos finales

Los archivos de trabajo cumplen una función legítima cuando registran versiones, fuentes, decisiones, identificadores y operaciones reproducibles. Esa función cambia en el manuscrito final: el método debe explicar qué se hizo y por qué, con lenguaje académico continuo, mientras los detalles operativos se conservan en el suplemento, la declaración de disponibilidad o el repositorio de materiales.

La ejecución no mantiene esa separación de forma consistente. La versión Word de *Suicidal Empathy* conserva:

- códigos internos como P0–P3, D-001 y localizadores `txt L99–205` sin una definición editorial suficiente;
- etiquetas y procedencia de producción como `TwExtract`, `IDs snowflake`, `v1.3-final` y “revisión compañera ES”;
- prosa de ledger trasladada al cuerpo: “Caso P0”, “Hecho”, “Omisión”, “Fuente”, “Circularidad” y “Aportación metodológica” como fragmentos nominales;
- lenguaje de combate y promoción: “primer golpe”, “desmontar”, “el libro aporta cero”, “por eso vende”, “rompe el hechizo” y apelaciones directas al lector;
- secuencias acumulativas de frases muy breves que producen ritmo de informe forense o hilo de red social, no de artículo científico.

El borrador del artículo B conserva los nombres X1–X5, `B-X4-v0.1`, `synthetic_coder_v0.2`, una lista literal de archivos `.md`, `.jsonl` y `.csv`, y una declaración provisional que todavía habla de “este borrador” y “scripts”. Estos datos pueden documentar reproducibilidad, pero requieren traducción a método académico y desplazamiento a materiales suplementarios.

El tercer manuscrito del portafolio de poder constituyente declara dentro del artículo que “se entrega en Markdown” y remite en notas a `corpus-oficial-cronologia.md` y a una “auditoría del expediente”. Ese texto expone el proceso interno en vez de presentar directamente el corpus, la clasificación y el razonamiento metodológico.

PAIDEIA muestra mejor continuidad de prosa. Aun así, el cuerpo incluye un hash de Git y enumera Vite, JavaScript, Supabase, PostgreSQL, Express y Socket.io. La descripción de las dos arquitecturas resulta pertinente; el hash y parte del stack pertenecen mejor a una nota de versión o suplemento técnico, salvo que el argumento dependa de una propiedad concreta de esos componentes.

Impacto: el lector percibe un artefacto ensamblado por etapas, disminuye la fluidez del argumento y puede asociar el manuscrito con una salida automática. La precisión técnica termina debilitando, en lugar de fortalecer, la credibilidad académica.

### P0. El proceso de revisión carece de un gate de prosa académica limpia

La referencia `writing-and-review.md` pide siete pasadas, pero el cierre no contiene un criterio observable que distinga:

- una oración académica completa de una etiqueta telegráfica;
- un método reproducible de un registro de operaciones;
- una declaración ética de IA de un relato técnico de elaboración;
- un término disciplinar necesario de un identificador interno del pipeline;
- una voz autoral firme de un tono promocional o adversarial.

Los scripts pueden verificar formato y detectar patrones; no deben reescribir la prosa ni imponer el ritmo de sus estructuras. La revisión final necesita una lectura limpia que reciba el manuscrito, la sede, las fuentes citadas y el perfil de voz autorizado, sin `ROUTE.md`, work items, checklists ni nombres de archivos internos.

Impacto: las siete pasadas pueden marcarse como completas mientras el documento conserva el lenguaje del sistema que lo produjo.

### P0. La validación estructural permite una falsa sensación de preparación académica

`route.py` valida rutas requeridas, frontmatter, work items, locks, enlaces y frescura del handoff. No interpreta `CLAIMS.md`, `VENUE.md`, las tarjetas de fuente, los gates éticos o los criterios de aceptación del trabajo. Esta frontera está declarada en `SKILL.md`, pero los agentes convierten con frecuencia un exit code 0 en “validado”, “blindado” o “listo”.

Evidencia:

- PAIDEIA pasa ambos checkpoints aunque usa estados fuera del vocabulario permitido: `supported-theoretically`, `protocol-derived` y `unverified/out-of-scope`.
- PAIDEIA contiene `CLAIMS 2.md`, `INQUIRY 2.md` y `manuscript/OUTLINE 2.md`; el contrato prohíbe archivos de estado paralelos y el validador no los reporta.
- El checkpoint `handoff` comprueba que las secciones intelectuales tengan texto, pero no comprueba coherencia con `ROUTE.md`.

Impacto: un agente nuevo puede interpretar “estructura válida” como “evidencia verificada” y avanzar hacia publicación con deuda oculta.

### P0. Un work item puede cerrarse con un output existente aunque el trabajo intelectual siga incompleto

`complete` demuestra propiedad, ruta regular y persistencia atómica. No registra criterios de aceptación, evidencia de verificación ni resultado del gate. En *Suicidal Empathy*, una tarjeta agregada reconoce que algunas fuentes secundarias no se cotejaron y enumera verificaciones pendientes, mientras los items y la primera versión editorial se cerraron.

El estado actual corrige el exceso: conserva el antiguo manuscrito como material de origen e invalida “listo para envío” por mezcla de diseños, ventana de X mal descrita y conclusiones excesivas.

Impacto: la unidad mecánica de “done” no corresponde a la unidad epistémica de “verificado”.

### P1. Los gates de venue no gobiernan realmente la adaptación editorial

PAIDEIA declara que no ha leído los diez artículos necesarios para la huella formal, pero ya eligió RED, trasladó el manuscrito a su plantilla y aprobó un paquete preenvío. `VENUE.md` también afirma que solo faltan metadatos del investigador, mientras el QA añade la huella, el archivo de la versión del software y otros pendientes.

Esto contradice el gate normativo que exige diez textos completos antes de considerar la huella terminada y pide evitar reestructuración guiada por venue antes de la decisión consecuencial.

Impacto: el proceso puede gastar esfuerzo de maquetación y adaptar la arquitectura a una sede cuyo ajuste intelectual aún es preliminar.

### P1. No existe una ruta de migración para proyectos creados con vocabularios anteriores

El proyecto sobre fascismo usa `current_cycle: refine`, mientras la versión instalada solo acepta `discover | argue | compose | audit`. También conserva el encabezado legado `## Private`. La suite prueba deliberadamente que el CLI no expone `migrate`.

Impacto: una mejora de seguridad rompe reinicios de proyectos reales y obliga a editar estado manualmente, precisamente la práctica que el CLI intenta evitar.

### P1. `ROUTE.md` y la sección intelectual de `HANDOFF.md` pueden discrepar sin que el checkpoint falle

En el proyecto sobre fascismo, `ROUTE.md` fija como acción exacta maquetar y enviar; `HANDOFF.md` fija primero la lectura autoral. El snapshot mecánico repite la acción canónica, mientras la sección intelectual conserva otra. Incluso después de migrar el ciclo y privacidad, esa contradicción seguiría siendo semánticamente peligrosa.

Impacto: un agente frío recibe dos instrucciones ejecutables y debe decidir cuál ignorar.

### P1. La activación implícita tiene falsos negativos

El portafolio de poder constituyente contiene tres artículos, varias sedes y continuidad multisesión. Cumple de forma directa la descripción de activación, pero solo conserva un handoff independiente. No existe `ROUTE.md`, ledger de claims, decisiones o fuentes.

Impacto: la continuidad depende de un resumen narrativo aunque el caso pertenece al núcleo de uso del skill.

Confianza: media. El registro permite demostrar ausencia de una raíz Research Route y presencia del proyecto después de la instalación; no permite demostrar por qué el router no activó la skill.

### P2. La semántica de fuentes y claims deriva entre proyectos

Las tarjetas de PAIDEIA usan un esquema abreviado y campos en español; las de *Suicidal Empathy* usan el esquema largo. `CLAIMS.md` también alterna estados canónicos, extensiones ad hoc y calificadores dentro del estado. La portabilidad depende entonces de inferencia textual del próximo agente.

Impacto: las búsquedas automatizadas, auditorías comparables y futuros checkpoints semánticos pierden precisión.

### P2. El benchmark no representa las operaciones que fallaron en producción local

Los resultados publicados reconocen que no usaron manuscrito vivo, texto completo, fallback real ni raíz externa, y que la mayoría de las mutaciones solo se propusieron. La evaluación mide buena forma de respuesta; no mide deriva durante veinte work items, edición manual de estado, contradicción entre artefactos, activación o degradación acumulada.

Impacto: la mediana 16,5/20 sobreestima la confianza para proyectos largos y file-backed.

## Fortalezas verificadas

- La instalación activa coincide con el repositorio auditado.
- `quick_validate.py` acepta el skill.
- Las 89 pruebas unitarias pasan.
- El CLI resiste carreras, symlinks, roots intercambiados, claims incompatibles y escrituras atómicas.
- `ROUTE.md` permitió corregir *Suicidal Empathy* sin borrar la historia: el estado actual identifica qué versión dejó de ser confiable y por qué.
- PAIDEIA conserva una delimitación intelectual útil: distingue infraestructura de evidencia, regulación formativa y eficacia empírica.
- La protección de material privado mejoró respecto del proyecto legado; las raíces nuevas ya no incluyen una sección privada en la plantilla.

## Recomendaciones priorizadas

### Iteración 0: crear una frontera editorial entre proceso y publicación

1. Separar cuatro capas: estado de investigación, materiales reproducibles, manuscrito académico y paquete editorial. El manuscrito no debe importar directamente texto del ledger.
2. Añadir `validate --checkpoint prose` con detección de frontmatter, rutas, extensiones de archivos, hashes, IDs internos, nombres de scripts, etiquetas de versión, TODO, “borrador”, “pendiente”, y léxico de sistema. Cada hallazgo debe permitir una excepción explícita para método, disponibilidad o declaración ética.
3. Añadir `validate --checkpoint release` que exija una lectura humana o clean-room con puntuación mínima de 4/5 en claridad, continuidad, registro académico, terminología, voz y ausencia de proceso interno.
4. Ejecutar la pasada clean-room en un contexto que solo reciba el manuscrito, la guía editorial, las afirmaciones verificadas y el perfil de voz autorizado. Los archivos Research Route permanecen fuera de esa pasada.
5. Limitar los scripts a detección, conteo y verificación. Toda reformulación sustantiva debe preservar significado, artículos, conectores, sujeto y verbo mediante revisión lingüística y aprobación autoral.
6. Crear una tabla de traducción de proceso a método. Por ejemplo, “X4 normalizó y versionó `B-X4-v0.1`” debe convertirse en “El corpus se normalizó, armonizó y deduplicó antes de la codificación”; el hash y los archivos se documentan en el suplemento.
7. Mantener la declaración de IA que exijan la revista y la ética académica, con una formulación concisa sobre funciones, verificación y responsabilidad. La transparencia no requiere narrar prompts, skills, scripts, iteraciones o arquitectura interna de Codex.
8. Añadir una lista de registros incompatibles con un artículo científico salvo justificación editorial: tono promocional, apelación directa al lector, lenguaje de combate, fragmentos nominales, anglicismos evitables, códigos de prioridad y secuencias de frases sin artículos o conectores.

Ejemplos de transformación:

- “El libro aporta cero. No hay escala, no hay alfa, no hay test-retest. Circularidad.” puede formularse como “El libro no presenta una escala ni evidencia de consistencia o estabilidad que permita evaluar empíricamente el constructo; por ello, la explicación conserva una estructura circular”.
- “Caso P0. Hecho. Omisión.” puede formularse como un párrafo que identifique la afirmación, describa la fuente primaria, explique la discrepancia y delimite su consecuencia inferencial.
- “La auditoría del expediente clasifica…” puede formularse como “Las fuentes se clasificaron según su carácter normativo, electoral o interpretativo y según el grado de definitividad del registro”.

### Iteración 1: impedir falsos verdes

1. Añadir `validate --checkpoint research` para comprobar un esquema parseable de claims, los cinco estados canónicos, evidencias enlazadas, tarjetas de fuente existentes, access level y campos críticos.
2. Añadir `validate --checkpoint venue` para exigir matriz, diez full texts, clases de conclusión y decisión aprobada antes de marcar una adaptación como lista.
3. Añadir `validate --checkpoint submission` que componga research, venue, ética, revisión, bibliografía y aprobación de versión exacta.
4. Detectar nombres que parezcan copias paralelas de artefactos canónicos, incluidos sufijos ` 2`, `copy`, `copia` y equivalentes configurables.
5. Cambiar la salida exitosa a `Structural validation passed; scholarly readiness not assessed` en todos los checkpoints estructurales.

### Iteración 2: cerrar el ciclo intelectual del work item

1. Añadir a cada item `acceptance`, `verification`, `gate` y `result` con esquema mínimo por tipo.
2. Exigir que `complete` reciba un registro de verificación o permita `complete --provisional` sin presentar el item como cerrado epistemológicamente.
3. Añadir tipos o checkpoints especializados para `source`, `venue`, `ethics`, `review` y `submission`.
4. Mantener un único estado de exact next action; generar la sección correspondiente del handoff desde `ROUTE.md` o exigir igualdad normalizada.

### Iteración 3: migración y ergonomía

1. Incorporar `route.py migrate --dry-run` con migraciones idempotentes para ciclos legados, handoff mecánico y privacidad.
2. Incorporar `route.py set-cycle` y comandos de actualización de estado para reducir reescrituras manuales de `ROUTE.md`.
3. Emitir al reanudar un diagnóstico de versión con instrucción exacta de migración.
4. Decidir si `refine` y `polish` son aliases de `audit` o estados explícitos; documentar una sola ontología.

### Iteración 4: evaluación basada en ejecuciones reales

1. Convertir PAIDEIA, *Suicidal Empathy* y fascismo en fixtures anonimizados de regresión.
2. Añadir pruebas de activación y no activación sobre sesiones reales.
3. Ejecutar recorridos de 10–25 items, reinicios fríos y cambios de venue o tesis.
4. Puntuar archivos producidos, no solo la respuesta final.
5. Repetir cada escenario con varias semillas/agentes y reportar dispersión, tasa de fallos críticos y tiempo hasta detectar el error.

## Criterios de éxito para la siguiente versión

- Ningún manuscrito de release contiene nombres de skills, scripts, work items, rutas locales, archivos internos, etiquetas de versión o códigos de proceso fuera de una sección justificada.
- Cada párrafo sustantivo contiene oraciones completas, conectores explícitos y un registro consistente con el género y la sede.
- La declaración de IA informa funciones y responsabilidad sin exponer el diario técnico de elaboración.
- Un revisor clean-room puede leer el documento sin inferir la arquitectura operativa usada para producirlo.
- El replay de *Suicidal Empathy* bloquea las versiones que conservan “P0”, `D-001`, `TwExtract`, `v1.3-final`, “revisión compañera ES” o fragmentos de ledger sin definición académica.
- Ningún proyecto con estados de claim no canónicos pasa `checkpoint research`.
- Ningún proyecto con copias paralelas pasa `checkpoint handoff` sin advertencia explícita.
- Ningún paquete adaptado a revista pasa `checkpoint venue` con menos de diez full texts o sin aprobación.
- Un proyecto legado recibe una migración reproducible, no instrucciones de edición manual.
- El replay de *Suicidal Empathy* bloquea “listo para depósito” mientras la tarjeta agregada declare verificación primaria pendiente.
- El replay de PAIDEIA diferencia “manuscrito completo” de “venue listo”.
- El handoff intelectual y la acción canónica nunca divergen.

## Verificación ejecutada

- `quick_validate.py research-route`: PASS.
- `python3 -m unittest discover -s tests -p 'test_route_cli.py' -v`: 89/89 PASS.
- PAIDEIA: `validate` PASS; `validate --checkpoint handoff` PASS.
- *Suicidal Empathy*: `validate` PASS; `validate --checkpoint handoff` PASS.
- Fascismo: ambos checkpoints FAIL por ciclo legado, handoff incompatible y privacidad heredada.

## Implementación posterior del plan v2

Después de esta auditoría se implementó una primera versión operativa de las recomendaciones:

- schema v2 opcional y migración v1 con `dry-run` y `apply`;
- clasificación adaptativa `routine`, `material` y `critical`;
- comando corto `advance` y revisiones agrupadas `argument` y `release`;
- checkpoints `research`, `venue`, `prose`, `release` y `submission`;
- inspección de prosa en Markdown, texto, LaTeX y DOCX, con excepciones ligadas a hash;
- capas `claims/` y `releases/`, criterios de aceptación, verificación y resultado en work items v2;
- orientación provisional de venue con tres textos completos y umbral de diez antes de submission.
- migración que normaliza ciclos legados `refine` y `polish`, regenera `HANDOFF.md` y deja los bloqueos de privacidad explícitos.

La suite ampliada pasa 100 pruebas y `quick_validate.py` pasa. Un replay sintético de cinco tareas redujo las invocaciones de CLI en 55,6 % y el tiempo local en 54,6 %. El porcentaje todavía requiere replay de proyectos académicos reales para generalizarse.
