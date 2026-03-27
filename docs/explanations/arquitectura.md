# Explicación: Arquitectura y decisiones de diseño

## Visión general

El proyecto está diseñado como un conjunto de **scripts independientes por métrica** que se ejecutan en paralelo dentro de un workflow de GitHub Actions, con un paso final de consolidación.

```
┌─────────────────────────────────────────────────────┐
│              GitHub Actions Workflow                 │
│                                                     │
│  generate-token ──┐                                 │
│                   ├── deployment-frequency (shards)  │
│  prepare ─────────┤                                 │
│                   ├── lead-time            (shards)  │
│                   ├── change-failure-rate  (shards)  │
│                   └── mttr                 (shards)  │
│                              │                      │
│                           merge                     │
│                        (consolidar)                 │
└─────────────────────────────────────────────────────┘
```

## Decisión: GitHub App para autenticación

**Alternativa descartada**: Fine-grained PAT o Token clásico como secret `GH_PAT`.

**Razón de la decisión**: con 500+ repos y hasta 1000 commits por repo, el rate-limit de 5,000 req/h de un PAT se agota rápidamente. Una GitHub App escala hasta 15,000 req/h y genera tokens temporales automáticos en cada ejecución.

**Implementación**: un job `generate-token` usa `actions/create-github-app-token@v1` y expone el token como output que los demás jobs consumen vía `needs.generate-token.outputs.token`.

## Decisión: shards fijos en lugar de input variable

**Alternativa descartada**: `shards` como input configurable del usuario.

**Razón de la decisión**: el valor óptimo de shards depende del tamaño de la organización y es estable entre ejecuciones. Exponerlo como input añade complejidad sin beneficio real. Se fijó en `SHARDS: 10` en el `env` global del workflow, calculado para 500 repos.

Para organizaciones más grandes, basta con editar el valor en el workflow una vez.

## Decisión: filtro de fechas opcional

**Problema**: organizaciones con años de histórico generan un volumen de datos innecesariamente alto para análisis recientes.

**Solución**: inputs opcionales `from_date` y `to_date` (YYYY-MM-DD) que se propagan como `FROM_DATE` y `TO_DATE` a todos los scripts. Cada script filtra los PRs por la fecha de merge relevante para su métrica.

**Comportamiento si no se proporcionan**: se procesan todos los PRs disponibles (compatibilidad con ejecuciones sin filtro).

## Decisión: scripts independientes versus monolito

**Alternativa descartada**: un solo script que calcula las 4 métricas en una ejecución.

**Razón de la decisión**: las métricas tienen diferentes costos en requests a la API:

| Métrica | Requests por repo |
|---|---|
| Deployment Frequency | Pocos (solo PRs a main) |
| Lead Time | Muchos (PRs + Compare API + commits) |
| Change Failure Rate | Pocos (solo PRs a main) |
| MTTR | Medio (PRs a main + Timeline API para hotfixes) |

Ejecutarlas por separado permite:

1. **Reintentar solo la métrica que falló** sin recalcular las demás.
2. **Obtener resultados parciales**: si Lead Time falla por rate-limit, Deployment Frequency y CFR ya tienen sus resultados.
3. **Escalabilidad**: cada métrica puede tener su propio `max-parallel` en el futuro.

## Decisión: sharding por repositorios

**Problema**: una organización con 500+ repos y miles de PRs agota rápidamente el rate-limit de la API de GitHub.

**Solución**: dividir la lista de repositorios en N shards. Cada shard es un job independiente que procesa solo su subconjunto.

**Implementación**:

1. Los repos se ordenan alfabéticamente (hace el sharding determinista).
2. Se dividen en N partes usando distribución equitativa (los primeros shards toman 1 extra si hay residuo).
3. `max-parallel: 3` limita la cantidad de shards ejecutándose simultáneamente para no competir por el rate-limit.

**Trade-off**: más shards = más jobs = más minutos de Actions consumidos, pero menor probabilidad de agotar el rate-limit y menor tiempo muro.

## Decisión: módulo `gh_helpers.py` compartido

**Problema**: las 4 métricas usan las mismas funciones HTTP, paginación y sharding.

**Solución**: extraer un módulo compartido `gh_helpers.py`.

**Ventaja**: un solo lugar para ajustar el manejo de rate-limit, headers, o lógica de paginación.

**Patrón**: cada script hace `sys.path.insert(0, os.path.dirname(__file__))` para importar el módulo sin necesidad de un `setup.py` o paquete instalable. Esto mantiene la simplicidad de ejecución con `python scripts/nombre.py`.

## Decisión: `api_get` retorna `Response`, no JSON

**Razón**: la función de paginación necesita acceder al header `Link` del response. Si `api_get` retornara solo `.json()`, se perdería la información de paginación.

Este fue un bug en la versión original del script (`get()` retornaba `.json()` y luego `get_all_prs` intentaba acceder a `.headers` sobre el JSON).

## Decisión: cruce por rama y tiempo, no por SHA

**Problema original**: el script previo intentaba cruzar commits entre develop→qa→main comparando SHAs. Esto falla cuando los PRs usan **squash merge** (GitHub genera un nuevo SHA en el merge).

**Solución**: en lugar de rastrear SHAs, se cruzan los PRs por:

1. **Nombre de rama**: un PR a QA cuyo `head.ref == "develop"` es un promotion de develop a QA.
2. **Orden temporal**: se busca el primer PR a QA cuya fecha de merge sea posterior al merge del PR a develop.

**Limitación**: si hay múltiples features mergeadas a develop antes de un solo PR a QA, todas se cruzan con el mismo PR de QA. Esto es correcto operativamente (todas se desplegaron a QA en el mismo batch).

## Decisión: clasificación de fallos por heurísticas de nomenclatura

**Problema**: GitHub no tiene un concepto nativo de "despliegue fallido". No existe una API que diga "este deploy causó un incidente".

**Solución**: usar convenciones de nomenclatura de ramas y títulos como proxy:

- `hotfix/*`, `bugfix/*`, `fix/*`, `revert-*` → indica una corrección.
- Título con "hotfix", "revert", "rollback" → indica una corrección.

**Alternativas consideradas**:

1. **Labels en PRs**: más preciso pero requiere que el equipo etiquete manualmente.
2. **GitHub Deployments API**: solo funciona si hay integraciones de CD configuradas.
3. **Issues vinculados**: parcialmente implementado en MTTR (se busca el issue vinculado para obtener la fecha de inicio del incidente).

**Recomendación**: si el equipo quiere mayor precisión, se puede agregar un label `incident` a los PRs de corrección y ajustar la clasificación.

## Decisión: variables de entorno para configuración

**Razón**: los scripts se ejecutan tanto en GitHub Actions (env vars vienen del workflow) como localmente (el usuario las exporta manualmente).

**Ventaja**: no se necesitan archivos de configuración, argumentos CLI ni dependencias adicionales.

**Convención**:
- `GH_TOKEN`: obligatorio, sin default.
- `GH_ORG`, `GH_TOPIC`: opcionales, con defaults sensatos.
- `SHARDS`, `SHARD_ID`: opcionales, default `1`/`1` (sin sharding).
- `FROM_DATE`, `TO_DATE`: opcionales, vacíos = sin filtro de fechas.
