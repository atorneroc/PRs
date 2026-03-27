# Referencia: Scripts de métricas DORA

Documentación técnica de cada script, sus funciones, variables de entorno y esquemas de salida.

## Módulo compartido: `gh_helpers.py`

Módulo HTTP reutilizado por todos los scripts de métricas. Provee paginación automática, manejo de rate-limit y sharding.

### Funciones

#### `api_get(url, params=None) → requests.Response | None`

Realiza una petición GET a la API de GitHub.

- **Parámetros**:
  - `url` (str): URL completa del endpoint.
  - `params` (dict, opcional): query-params adicionales.
- **Retorno**: objeto `Response` de requests si el status es 200, o `None` si hay error.
- **Comportamiento ante rate-limit**: si recibe un 403 con `X-RateLimit-Remaining: 0`, calcula el tiempo de espera a partir de `X-RateLimit-Reset` y reintenta automáticamente.

#### `api_get_paginated(url, params=None) → list`

Consume un endpoint paginado completo siguiendo el header `Link: <url>; rel="next"`.

- **Parámetros**:
  - `url` (str): URL del primer request.
  - `params` (dict, opcional): query-params iniciales. Se usa `per_page=100` por defecto.
- **Retorno**: lista con todos los items de todas las páginas.
- **Nota**: después de la primera página, los `params` se ignoran porque la URL de `next` ya incluye los query-params.

#### `get_repos_by_topic(org, topic) → list[dict]`

Obtiene todos los repositorios de una organización filtrados por un topic.

- **Parámetros**:
  - `org` (str): nombre de la organización en GitHub.
  - `topic` (str): topic a filtrar.
- **Retorno**: lista de objetos repo de la API.

#### `get_prs(org, repo_name, base, state="closed") → list[dict]`

Obtiene todos los PRs paginados hacia una rama base.

- **Parámetros**:
  - `org` (str): organización.
  - `repo_name` (str): nombre del repositorio.
  - `base` (str): rama destino (`develop`, `qa`, `main`).
  - `state` (str): estado del PR (`closed`, `open`, `all`).
- **Retorno**: lista de objetos PR de la API.

#### `get_pr_commits(org, repo_name, pr_number) → list[dict]`

Obtiene todos los commits de un PR (paginado, máximo 250 por limitación de la API).

- **Parámetros**:
  - `org` (str): organización.
  - `repo_name` (str): repositorio.
  - `pr_number` (int): número del PR.
- **Retorno**: lista de objetos commit.

#### `shard_slice(items, shards, shard_id) → list`

Retorna el subconjunto de items correspondiente a un shard específico.

- **Parámetros**:
  - `items` (list): lista a dividir.
  - `shards` (int): número total de shards.
  - `shard_id` (int): ID del shard actual (1-based).
- **Retorno**: sub-lista de items.
- **Distribución**: los primeros `remainder` shards toman 1 elemento extra para distribución equitativa.

---

## `deployment_frequency.py`

Calcula la **Deployment Frequency**: cantidad de despliegues a producción.

### Variables de entorno

| Variable | Requerida | Default | Descripción |
|---|---|---|---|
| `GH_TOKEN` | Sí | — | Token de GitHub |
| `GH_ORG` | No | `CCAPITAL-APPS` | Organización |
| `GH_TOPIC` | No | `tribu-canal-digital` | Topic de filtrado |
| `SHARDS` | No | `1` | Total de shards |
| `SHARD_ID` | No | `1` | ID del shard actual |
| `OUT_FILE` | No | `deploy_freq_shard_{ID}_of_{N}.csv` | Ruta del CSV de salida |
| `FROM_DATE` | No | *(vacío)* | Fecha inicial del análisis (YYYY-MM-DD). Filtra por `merged_at` del PR a main |
| `TO_DATE` | No | *(vacío)* | Fecha final del análisis (YYYY-MM-DD). Filtra por `merged_at` del PR a main |

### Esquema de salida CSV

| Columna | Tipo | Descripción |
|---|---|---|
| `repo_name` | string | Nombre del repositorio |
| `pr_number` | int | Número del PR |
| `title` | string | Título del PR |
| `source_branch` | string | Rama origen |
| `merged_to_main_at` | ISO 8601 | Fecha y hora del merge |
| `year_week` | string | Semana (`YYYY-Www`) |
| `year_month` | string | Mes (`YYYY-MM`) |

---

## `lead_time.py`

Calcula el **Lead Time for Changes**: tiempo desde el primer commit hasta producción.

### Variables de entorno

Mismas que `deployment_frequency.py`, incluyendo `FROM_DATE` y `TO_DATE`. El `OUT_FILE` por defecto es `lead_time_shard_{ID}_of_{N}.csv`.

> En Lead Time, el filtro de fechas se aplica sobre la fecha de merge a `develop` (no a main), ya que es el evento de entrada que origina el cálculo del ciclo completo.

### Funciones adicionales

#### `get_branch_first_commit(org, repo_name, branch, base="develop") → str | None`

Usa la Compare API para obtener la fecha del primer commit exclusivo de una rama respecto a `develop`.

- **Endpoint**: `GET /repos/{org}/{repo}/compare/{base}...{branch}`
- **Retorno**: fecha ISO 8601 del primer commit, o `None` si la rama no existe o no tiene commits exclusivos.

### Esquema de salida CSV

| Columna | Tipo | Descripción |
|---|---|---|
| `repo_name` | string | Repositorio |
| `source_branch` | string | Rama feature |
| `first_commit_date` | ISO 8601 | Fecha del primer commit |
| `pr_to_develop_id` | int | PR mergeado a develop |
| `merged_to_develop_at` | ISO 8601 | Fecha merge a develop |
| `pr_to_qa_id` | int / null | PR mergeado a qa |
| `merged_to_qa_at` | ISO 8601 / null | Fecha merge a qa |
| `pr_to_main_id` | int / null | PR mergeado a main |
| `merged_to_main_at` | ISO 8601 / null | Fecha merge a main |
| `cycle_time_days` | float / null | Días desde primer commit hasta main |

---

## `change_failure_rate.py`

Calcula el **Change Failure Rate**: porcentaje de despliegues que son correcciones.

### Variables de entorno

Mismas que `deployment_frequency.py`, incluyendo `FROM_DATE` y `TO_DATE`. El `OUT_FILE` por defecto es `cfr_shard_{ID}_of_{N}.csv`.

### Funciones adicionales

#### `classify_pr(pr) → tuple[bool, str | None]`

Clasifica un PR como fallo o no según reglas de pattern matching.

- **Patterns de rama**: `^(hotfix|bugfix|fix|revert)[/\-]` (case-insensitive)
- **Patterns de título**: `\b(hotfix|revert|rollback)\b` (case-insensitive)
- **Retorno**: `(True, "branch: hotfix/fix-123")` o `(False, None)`

### Esquema de salida CSV

| Columna | Tipo | Descripción |
|---|---|---|
| `repo_name` | string | Repositorio |
| `pr_number` | int | Número del PR |
| `title` | string | Título del PR |
| `source_branch` | string | Rama origen |
| `merged_to_main_at` | ISO 8601 | Fecha merge |
| `is_failure` | bool | `True` si es hotfix/revert |
| `failure_reason` | string / null | Motivo de clasificación |
| `year_month` | string | Mes (`YYYY-MM`) |

---

## `mttr.py`

Calcula el **Mean Time to Recovery**: tiempo de recuperación ante fallos.

### Variables de entorno

Mismas que `deployment_frequency.py`, incluyendo `FROM_DATE` y `TO_DATE`. El `OUT_FILE` por defecto es `mttr_shard_{ID}_of_{N}.csv`.

> En MTTR, el filtro de fechas se aplica sobre la fecha de merge a `main` (fecha de resolución del incidente).

### Funciones adicionales

#### `is_failure_pr(pr) → bool`

Determina si un PR es de tipo hotfix/revert usando los mismos patterns que `classify_pr`.

#### `get_linked_issue_created_at(org, repo_name, pr_number) → str | None`

Busca un issue vinculado al PR a través de la Timeline API.

- **Endpoint**: `GET /repos/{org}/{repo}/issues/{pr_number}/timeline`
- **Busca**: eventos de tipo `cross-referenced` con un issue asociado.
- **Retorno**: fecha `created_at` del issue vinculado, o `None`.

### Esquema de salida CSV

| Columna | Tipo | Descripción |
|---|---|---|
| `repo_name` | string | Repositorio |
| `pr_number` | int | Número del PR hotfix/revert |
| `title` | string | Título del PR |
| `source_branch` | string | Rama del hotfix |
| `incident_start` | ISO 8601 | Inicio del incidente |
| `incident_source` | string | `issue` o `pr_created` |
| `merged_to_main_at` | ISO 8601 | Fecha del fix en producción |
| `recovery_hours` | float | Horas de recuperación |
| `year_month` | string | Mes (`YYYY-MM`) |

---

## `merge_shards.py`

Consolida los CSVs de todos los shards y genera un resumen ejecutivo.

### Variables de entorno

| Variable | Requerida | Default | Descripción |
|---|---|---|---|
| `OUTPUT_DIR` | No | `.` | Directorio de salida |

### Patrones de archivos esperados

| Métrica | Glob pattern |
|---|---|
| Deployment Frequency | `deploy_freq_shard_*.csv` |
| Lead Time | `lead_time_shard_*.csv` |
| Change Failure Rate | `cfr_shard_*.csv` |
| MTTR | `mttr_shard_*.csv` |

### Archivos de salida

| Archivo | Descripción |
|---|---|
| `dora_deployment_frequency.csv` | Consolidación de todos los shards de DF |
| `dora_lead_time.csv` | Consolidación de todos los shards de LT |
| `dora_change_failure_rate.csv` | Consolidación de todos los shards de CFR |
| `dora_mttr.csv` | Consolidación de todos los shards de MTTR |
| `dora_summary.csv` | Resumen ejecutivo mensual de las 4 métricas |
