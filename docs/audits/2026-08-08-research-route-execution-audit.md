# Auditoría de ejecuciones de Research Route Slim

Fecha: 2026-08-08  
Alcance: revisión de consistencia documental, validación determinista, pruebas automatizadas y benchmark publicado.

## Dictamen

Research Route Slim aporta continuidad entre sesiones y una base sólida para la integridad de archivos, la concurrencia y la transferencia mecánica de trabajo. La validación estructural no demuestra por sí sola la calidad intelectual, la suficiencia de las fuentes, el ajuste a una sede editorial ni la aprobación autoral final.

## Método y cobertura

1. Se compararon los artefactos publicados con la implementación y las instrucciones instalables.
2. Se revisaron las rutas de validación, los checkpoints y las pruebas automatizadas.
3. Se contrastaron los resultados del benchmark con las operaciones que el CLI realmente ejecuta.
4. Se inspeccionaron ejemplos de continuidad, adaptación editorial y migración desde estados anteriores.

## Hallazgos

### P0. La frontera entre proceso y publicación necesita un gate explícito

Los archivos de trabajo pueden conservar versiones, fuentes, decisiones e identificadores para reproducibilidad. El manuscrito final debe traducir esa información a método académico continuo y reservar los detalles operativos para un suplemento, una declaración de disponibilidad o un repositorio de materiales.

### P0. La validación estructural puede producir una falsa sensación de preparación académica

Los checkpoints actuales verifican rutas, frontmatter, locks, enlaces, hashes y persistencia. No interpretan por sí solos la evidencia de claims, los gates éticos, la bibliografía, la calidad de la prosa ni el juicio del revisor. La salida debe distinguir con claridad integridad estructural de preparación académica.

### P1. Los gates de venue y submission deben gobernar el avance editorial

La adaptación a una sede requiere una matriz de requisitos, textos completos suficientes, una decisión de ajuste y aprobación de la versión exacta. Esas condiciones deben bloquear el cierre cuando falte evidencia, aunque la estructura de archivos sea válida.

### P1. Los proyectos legados necesitan una migración reproducible

Los ciclos y encabezados anteriores deben transformarse mediante un comando idempotente y auditable. La edición manual de documentos de estado no debe ser el único camino para reanudar un proyecto existente.

### P1. La acción canónica y el handoff deben permanecer sincronizados

El siguiente paso ejecutable debe tener una sola fuente de verdad. Si el resumen intelectual y la acción canónica divergen, el checkpoint debe fallar o emitir un bloqueo explícito.

### P2. El benchmark debe cubrir recorridos file-backed y reinicios fríos

Las pruebas de respuesta no sustituyen recorridos que creen artefactos, completen múltiples work items, cambien de sede, reinicien el proceso y detecten contradicciones entre documentos. La evaluación debe publicar también dispersión, fallos críticos y tiempo hasta la detección.

## Fortalezas verificadas

- La instalación publicada coincide con el paquete auditado.
- Las pruebas cubren carreras, symlinks, raíces intercambiadas, claims incompatibles y escrituras atómicas.
- El handoff conserva una ruta reproducible para reabrir decisiones sin borrar la historia.
- La plantilla separa el estado operativo de los materiales que deben llegar al manuscrito.

## Recomendaciones priorizadas

1. Mantener separados estado de investigación, materiales reproducibles, manuscrito académico y paquete editorial.
2. Añadir checkpoints explícitos para investigación, venue, prosa, release y submission, con mensajes que indiquen qué queda fuera de la validación estructural.
3. Exigir criterios de aceptación, verificación y resultado en cada work item antes de marcarlo como completo.
4. Implementar migración idempotente para ciclos y handoffs legados.
5. Añadir fixtures anonimizados y recorridos file-backed de 10–25 tareas con reinicios fríos y cambios de sede.

## Verificación ejecutada

- Validación del skill y compilación del CLI.
- Suite unitaria y pruebas de integración del paquete.
- Checkpoints de validación estructural y handoff.
- Replay sintético file-backed con creación, reclamación, cierre y transferencia de tareas.

## Estado de la implementación v2

La versión v2 incorpora schema opcional, migración, clasificación adaptativa, `advance`, revisiones agrupadas, checkpoints adicionales, inspección de prosa, capas de claims y releases, criterios de aceptación y orientación de venue. Las pruebas de regresión cubren además deuda material, aprobación de release obsoleta, outputs faltantes y replay file-backed.
