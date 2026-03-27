# Tutorial: Inicio rápido con DORA Metrics

Este tutorial te guía paso a paso para ejecutar tu primer reporte de métricas DORA desde GitHub Actions.

## Objetivo

Al finalizar, tendrás un archivo CSV con las 4 métricas DORA calculadas para todos los repositorios de tu organización filtrados por topic.

## Prerrequisitos

- Acceso de administrador al repositorio donde está este proyecto
- Una GitHub App configurada en la organización (ver [setup de GitHub App](../how-to-guides/setup-github-app.md))
- Repositorios destino con flujo de ramas: `feature → develop → qa → main`

## Paso 1: Configurar los secrets de la GitHub App

1. Ve a **Settings → Secrets and variables → Actions** en tu repositorio.
2. Crea el secret `APP_ID` con el ID numérico de tu GitHub App.
3. Crea el secret `APP_PRIVATE_KEY` con la clave privada completa de tu GitHub App.

Consulta la [guía de setup de GitHub App](../how-to-guides/setup-github-app.md) para obtener estos valores.

## Paso 2: Ejecutar el workflow

1. Ve a la pestaña **Actions** del repositorio.
2. En el panel izquierdo, selecciona **DORA Metrics**.
3. Selecciona **Run workflow**.
4. Configura los parámetros:

| Parámetro | Descripción | Valor por defecto |
|---|---|---|
| `org` | Organización de GitHub | `CCAPITAL-APPS` |
| `topic` | Topic para filtrar repositorios | `tribu-canal-digital` |
| `from_date` | Fecha inicial del análisis (YYYY-MM-DD) | *(vacío = sin límite)* |
| `to_date` | Fecha final del análisis (YYYY-MM-DD) | *(vacío = sin límite)* |

5. Selecciona **Run workflow**.

## Paso 3: Monitorear la ejecución

El workflow ejecuta 7 jobs:

1. **generate-token** — Genera un token temporal de GitHub App.
2. **prepare** — Genera la matriz de shards (10 fijos).
3. **deployment-frequency** — Calcula la frecuencia de despliegues (10 shards, max 3 en paralelo).
4. **lead-time** — Calcula el lead time (10 shards, max 3 en paralelo).
5. **change-failure-rate** — Calcula la tasa de fallos (10 shards, max 3 en paralelo).
6. **mttr** — Calcula el tiempo de recuperación (10 shards, max 3 en paralelo).
7. **merge** — Consolida todos los CSVs en reportes finales.

## Paso 4: Descargar los resultados

1. Una vez completado el workflow, ve al run correspondiente.
2. En la sección **Artifacts**, descarga `dora-metrics-report`.
3. El ZIP contiene:

| Archivo | Contenido |
|---|---|
| `dora_deployment_frequency.csv` | Todos los despliegues a producción |
| `dora_lead_time.csv` | Cycle time de cada feature branch |
| `dora_change_failure_rate.csv` | Clasificación de cada PR como fallo o no |
| `dora_mttr.csv` | Incidentes con horas de recuperación |
| `dora_summary.csv` | Resumen mensual de las 4 métricas |

## Paso 5: Interpretar el resumen

El archivo `dora_summary.csv` contiene una fila por métrica por mes:

```csv
year_month,metric,value,unit
2026-01,deployment_frequency,42,deploys/month
2026-01,lead_time_median,3.5,days
2026-01,change_failure_rate,12.3,%
2026-01,mttr,6.75,hours
```

Consulta la [explicación del modelo DORA](../explanations/modelo-dora.md) para entender cómo clasificar tu equipo según estos valores.

## Paso 6 (opcional): Acotar el período de análisis

Si la organización tiene mucho histórico, usa los campos `from_date` y `to_date` para limitar el rango. Por ejemplo, para analizar solo el último trimestre:

- **from_date**: `2026-01-01`
- **to_date**: `2026-03-31`

Esto reduce la cantidad de datos procesados y el consumo de rate-limit.

## Siguiente paso

- [Ajustar el sharding para organizaciones grandes](../how-to-guides/ajustar-sharding.md)
- [Interpretar los resultados](../how-to-guides/interpretar-resultados.md)
