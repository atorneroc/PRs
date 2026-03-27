# Guía: Interpretar los resultados de las métricas DORA

Esta guía explica cómo leer y analizar los archivos CSV generados por el workflow.

## Archivos de salida

### `dora_summary.csv` — Resumen ejecutivo

Este es el archivo principal. Contiene las 4 métricas agregadas por mes.

| Columna | Descripción |
|---|---|
| `year_month` | Mes en formato `YYYY-MM` |
| `metric` | Nombre de la métrica |
| `value` | Valor numérico |
| `unit` | Unidad de medida |

Ejemplo de lectura:

```csv
year_month,metric,value,unit
2026-01,deployment_frequency,42,deploys/month
2026-01,lead_time_median,3.5,days
2026-01,change_failure_rate,12.3,%
2026-01,mttr,6.75,hours
```

Interpretación del ejemplo:
- En enero 2026, hubo **42 despliegues** a producción.
- La mediana de lead time fue **3.5 días**.
- El **12.3%** de los despliegues fueron correcciones (hotfix/revert).
- Los fallos se resolvieron en promedio en **6.75 horas**.

### Clasificación DORA

| Métrica | Elite | High | Medium | Low |
|---|---|---|---|---|
| Deployment Frequency | Múltiples/día | Semanal | Mensual | > 6 meses |
| Lead Time | < 1 día | 1 día – 1 semana | 1 semana – 1 mes | > 6 meses |
| Change Failure Rate | 0–15% | 16–30% | 31–45% | > 45% |
| MTTR | < 1 hora | < 1 día | < 1 semana | > 6 meses |

## Archivos detallados

### `dora_deployment_frequency.csv`

Una fila por cada PR mergeado a `main`.

| Columna | Descripción |
|---|---|
| `repo_name` | Nombre del repositorio |
| `pr_number` | Número del PR |
| `title` | Título del PR |
| `source_branch` | Rama origen del PR |
| `merged_to_main_at` | Fecha y hora del merge a main |
| `year_week` | Semana del año (`YYYY-Www`) |
| `year_month` | Mes (`YYYY-MM`) |

### `dora_lead_time.csv`

Una fila por cada PR mergeado a `develop`.

| Columna | Descripción |
|---|---|
| `repo_name` | Repositorio |
| `source_branch` | Rama feature |
| `first_commit_date` | Fecha del primer commit en la rama feature |
| `pr_to_develop_id` | PR que mergeó a develop |
| `merged_to_develop_at` | Fecha merge a develop |
| `pr_to_qa_id` | PR que mergeó a qa |
| `merged_to_qa_at` | Fecha merge a qa |
| `pr_to_main_id` | PR que mergeó a main |
| `merged_to_main_at` | Fecha merge a main |
| `cycle_time_days` | Tiempo total en días (primer commit → main) |

### `dora_change_failure_rate.csv`

Una fila por cada PR mergeado a `main`, clasificado.

| Columna | Descripción |
|---|---|
| `repo_name` | Repositorio |
| `pr_number` | Número del PR |
| `title` | Título del PR |
| `source_branch` | Rama origen |
| `merged_to_main_at` | Fecha merge a main |
| `is_failure` | `True` si es hotfix/revert, `False` si no |
| `failure_reason` | Motivo de la clasificación |
| `year_month` | Mes |

### `dora_mttr.csv`

Una fila por cada incidente (hotfix/revert mergeado a main).

| Columna | Descripción |
|---|---|
| `repo_name` | Repositorio |
| `pr_number` | Número del PR hotfix/revert |
| `title` | Título del PR |
| `source_branch` | Rama del hotfix |
| `incident_start` | Inicio del incidente (issue o PR created_at) |
| `incident_source` | `issue` o `pr_created` |
| `merged_to_main_at` | Fecha del fix en producción |
| `recovery_hours` | Horas de recuperación |
| `year_month` | Mes |

## Acciones recomendadas según resultados

| Situación | Acción |
|---|---|
| Lead Time > 7 días | Revisar cuellos de botella en el flujo develop → qa → main |
| CFR > 30% | Reforzar revisión de código y testing antes de main |
| MTTR > 24 horas | Revisar procesos de respuesta a incidentes |
| DF < 4/mes | Evaluar si el flujo de ramas impone overhead excesivo |
