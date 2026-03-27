# Referencia: Workflow de GitHub Actions

Documentación técnica del workflow `.github/workflows/cycle-time.yml`.

## Nombre del workflow

**DORA Metrics**

## Trigger

`workflow_dispatch` (ejecución manual desde la UI de GitHub Actions).

### Inputs

| Input | Tipo | Requerido | Default | Descripción |
|---|---|---|---|---|
| `org` | string | Sí | `CCAPITAL-APPS` | Organización de GitHub |
| `topic` | string | Sí | `tribu-canal-digital` | Topic para filtrar repositorios |
| `from_date` | string | No | *(vacío)* | Fecha inicial del análisis (YYYY-MM-DD) |
| `to_date` | string | No | *(vacío)* | Fecha final del análisis (YYYY-MM-DD) |

> `shards` no es un input. Está fijado en **10** dentro del bloque `env` del workflow.

## Variables de entorno globales

```yaml
env:
  GH_ORG: ${{ github.event.inputs.org }}
  GH_TOPIC: ${{ github.event.inputs.topic }}
  SHARDS: 10
  FROM_DATE: ${{ github.event.inputs.from_date }}
  TO_DATE: ${{ github.event.inputs.to_date }}
```

Estas variables se propagan automáticamente a todos los jobs. Los jobs de métricas añaden a nivel de job `GH_TOKEN` y `SHARD_ID`, que se fusionan con las globales.

## Secrets requeridos

| Secret | Descripción |
|---|---|
| `APP_ID` | ID numérico de la GitHub App |
| `APP_PRIVATE_KEY` | Clave privada de la GitHub App (formato PEM) |

## Jobs

### 0. `generate-token`

Genera un token temporal de GitHub App válido para la ejecución.

- **Depende de**: nada
- **Acción**: `actions/create-github-app-token@v1`
- **Output**: `token` — token de instalación de la GitHub App
- **Duración**: segundos

### 1. `prepare`

Genera la matriz de shards para los jobs posteriores.

- **Depende de**: nada
- **Output**: `matrix` — JSON con `{"shard_id": [1, 2, ..., 10]}`
- **Duración**: segundos

### 2. `deployment-frequency`

Ejecuta `scripts/deployment_frequency.py` para cada shard.

- **Depende de**: `prepare`, `generate-token`
- **Estrategia**: `matrix` con `max-parallel: 3`, `fail-fast: false`
- **Env adicional**: `GH_TOKEN` (del job `generate-token`), `SHARD_ID` (de la matriz)
- **Artifact**: `df-shard-{ID}` → `deploy_freq_shard_*.csv`

### 3. `lead-time`

Ejecuta `scripts/lead_time.py` para cada shard.

- **Depende de**: `prepare`, `generate-token`
- **Estrategia**: `matrix` con `max-parallel: 3`, `fail-fast: false`
- **Env adicional**: `GH_TOKEN`, `SHARD_ID`
- **Artifact**: `lt-shard-{ID}` → `lead_time_shard_*.csv`

### 4. `change-failure-rate`

Ejecuta `scripts/change_failure_rate.py` para cada shard.

- **Depende de**: `prepare`, `generate-token`
- **Estrategia**: `matrix` con `max-parallel: 3`, `fail-fast: false`
- **Env adicional**: `GH_TOKEN`, `SHARD_ID`
- **Artifact**: `cfr-shard-{ID}` → `cfr_shard_*.csv`

### 5. `mttr`

Ejecuta `scripts/mttr.py` para cada shard.

- **Depende de**: `prepare`, `generate-token`
- **Estrategia**: `matrix` con `max-parallel: 3`, `fail-fast: false`
- **Env adicional**: `GH_TOKEN`, `SHARD_ID`
- **Artifact**: `mttr-shard-{ID}` → `mttr_shard_*.csv`

### 6. `merge`

Consolida todos los CSV parciales en reportes finales.

- **Depende de**: `deployment-frequency`, `lead-time`, `change-failure-rate`, `mttr`
- **Descarga**: artifacts que coincidan con `{df,lt,cfr,mttr}-shard-*`
- **Script**: `scripts/merge_shards.py`
- **Artifact final**: `dora-metrics-report` (retención: 30 días)

## Diagrama de ejecución

```
generate-token ──┐
                 ├── deployment-frequency (shard 1..10, max 3 paralelos)
prepare ─────────┤
                 ├── lead-time            (shard 1..10, max 3 paralelos)
                 ├── change-failure-rate  (shard 1..10, max 3 paralelos)
                 └── mttr                 (shard 1..10, max 3 paralelos)
                            └── merge (consolida todo)
```

## Artifacts generados

| Nombre | Retención | Contenido |
|---|---|---|
| `df-shard-{ID}` | 5 días | CSV parcial de Deployment Frequency |
| `lt-shard-{ID}` | 5 días | CSV parcial de Lead Time |
| `cfr-shard-{ID}` | 5 días | CSV parcial de Change Failure Rate |
| `mttr-shard-{ID}` | 5 días | CSV parcial de MTTR |
| `dora-metrics-report` | 30 días | 5 CSVs consolidados finales |

## Filtro por rango de fechas

Cuando se proporcionan `from_date` y/o `to_date`, cada script filtra los PRs según la fecha de merge relevante para su métrica:

| Métrica | Campo filtrado |
|---|---|
| Deployment Frequency | `merged_at` del PR a `main` |
| Lead Time | `merged_at` del PR a `develop` |
| Change Failure Rate | `merged_at` del PR a `main` |
| MTTR | `merged_at` del PR hotfix/revert a `main` |

Si no se proporcionan fechas, se procesan todos los PRs disponibles.
