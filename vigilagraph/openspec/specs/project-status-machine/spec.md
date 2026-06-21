# Especificación: Project Status Machine

> Máquina de estados del proyecto — hook de transición a collecting y UI asociada.

---

## Requerimiento: Hook transition → collecting

`transition_status` DETECTA `to_status="collecting"` y ejecuta side effects ANTES de escribir:

1. Validar `project.search_strategy` existe → si no, 422.
2. Validar `sources_selected` incluye "openalex" → si no, 422.
3. Crear `CollectionRun(project_id, source_name="openalex", status="pending")`.
4. Encolar `collect_from_source.delay(collection_run_id=str(run.id))`.

- Feliz: draft + search strategy + openalex → collecting, CollectionRun creado, tarea encolada.
- Error: sin SearchStrategy → 422, status NO cambia.
- Error: sources_selected sin openalex → 422, status NO cambia.
- Error: ya collecting en curso → 409.
- Regla: fallar rápido — validaciones antes de toda escritura.

## Requerimiento: Botón "Collect Now" (NUEVO, UI)

Overview (`page.tsx`) muestra botón "Collect Now" solo en status `draft`. Llama `POST /projects/{id}/collect`.

- Feliz: clic → loading → 202 → proyecto pasa a collecting.
- Edge: ya collecting → botón deshabilitado + tooltip.
- Edge: sin search strategy → botón deshabilitado + tooltip.
