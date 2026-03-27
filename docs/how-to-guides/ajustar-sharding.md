# Guía: Ajustar el sharding para organizaciones grandes

Esta guía explica cómo funciona el sistema de sharding y cómo modificarlo si es necesario.

## Configuración actual

El workflow usa **10 shards fijos** (definidos en `env.SHARDS` del workflow, no como input del usuario). Cada métrica ejecuta hasta **3 shards en paralelo** (`max-parallel: 3`).

Con 500 repos, cada shard procesa ~50 repos.

## Cómo funciona el sharding

1. El script obtiene la lista de repos filtrados por topic.
2. Los ordena alfabéticamente (determinista).
3. Divide la lista en N partes iguales (shards).
4. Cada job procesa solo su parte asignada.

Ejemplo con 500 repos y 10 shards:

| Shard | Repos procesados |
|---|---|
| 1 | repos 1–50 |
| 2 | repos 51–100 |
| ... | ... |
| 10 | repos 451–500 |

## ¿10 o 20 shards?

### Comparativa con 500 repos y max-parallel: 3

| Aspecto | 10 shards | 20 shards |
|---|---|---|
| Repos por shard | 50 | 25 |
| Rondas por métrica | 4 (ceil(10/3)) | 7 (ceil(20/3)) |
| Jobs totales (4 métricas) | 40 | 80 |
| Concurrencia máxima | 12 jobs (4×3) | 12 jobs (4×3) |
| Overhead total | ~40 jobs × 40s ≈ 27 min | ~80 jobs × 40s ≈ 53 min |

### Tiempo estimado (caso pesimista: 1000 commits/repo)

**Supuestos**: ~35 requests/repo (con filtro de fechas activo), ~1s por request.

| Configuración | Tiempo por shard | Rondas | Tiempo muro total por métrica |
|---|---|---|---|
| 10 shards, max-parallel: 3 | ~29 min | 4 | ~117 min |
| 20 shards, max-parallel: 3 | ~15 min | 7 | ~106 min |
| 20 shards, max-parallel: 5 | ~15 min | 4 | ~60 min |

### Impacto en minutos facturables

Los minutos de Actions facturables son la **suma de duración de todos los jobs**, no el tiempo muro. Como el trabajo total es el mismo (misma cantidad de repos y requests), los minutos facturables son similares entre 10 y 20 shards, con un incremento leve en 20 shards por el overhead adicional de spin-up.

### Recomendación

| Escenario | Shards | max-parallel | Nota |
|---|---|---|---|
| ≤ 100 repos | 5 | 3 | Conservador y suficiente |
| 100–500 repos | 10 | 3 | Configuración actual (default) |
| 500+ repos con GitHub App | 20 | 5 | Más rápido aprovechando el rate-limit de 10,000–15,000 req/h |

Para subir a 20 shards, edita el workflow:

```yaml
env:
  SHARDS: 20
```

Y opcionalmente, sube `max-parallel` en cada job de métrica:

```yaml
strategy:
  max-parallel: 5
```

> **Nota**: con `max-parallel: 5` y 4 métricas simultáneas, el pico es 20 jobs concurrentes. Verifica que tu plan de GitHub Actions lo soporte (gratis = 20 concurrent, Team = 60, Enterprise = 180).

## Rate-limit por tipo de token

| Tipo de token | Límite/hora | Shards recomendados |
|---|---|---|
| Token clásico | 5,000 | 5–10 |
| Fine-grained PAT | 5,000 | 5–10 |
| GitHub App (< 20 users) | 5,000 | 5–10 |
| GitHub App (20+ users) | 5,000 + 50/user (max 15,000) | 10–20 |

## Calcular el número óptimo de shards

### Estimación de requests por repo

| Operación | Requests por repo (aprox.) |
|---|---|
| Listar PRs a develop | 1–5 (paginado) |
| Listar PRs a qa | 1–3 |
| Listar PRs a main | 1–3 |
| Commits por PR | 1 por PR |
| Compare API (Lead Time) | 1 por PR mergeado a develop |
| Timeline API (MTTR) | 1 por hotfix PR |

**Estimación conservadora**: ~50–200 requests por repo (depende del volumen de PRs).

### Fórmula

```
shards = ceil(total_repos × requests_por_repo / 4000)
```

Se usa 4,000 en lugar de 5,000 para dejar margen.

## Control de paralelismo

El workflow usa `max-parallel: 3` para que no se ejecuten todos los shards al mismo tiempo. Esto evita que múltiples shards compitan por el rate-limit.

Si usas una **GitHub App** con rate-limit de 10,000+/h, puedes aumentar `max-parallel` a 5.

## Ejecución local con sharding

Puedes ejecutar un shard específico localmente:

```bash
export GH_TOKEN="ghp_tutoken"
export GH_ORG="CCAPITAL-APPS"
export GH_TOPIC="tribu-canal-digital"
export SHARDS=10
export SHARD_ID=1

python scripts/deployment_frequency.py
```

Esto procesará solo los repos del shard 1 de 10.

## Verificar qué repos procesa cada shard

Al ejecutar cualquier script, las primeras líneas del log muestran:

```
=== Deployment Frequency — Shard 1/10 — CCAPITAL-APPS/tribu-canal-digital ===
Total repos con topic 'tribu-canal-digital': 500
Repos a procesar: ['repo-alpha', 'repo-beta', 'repo-gamma', ...]
```
