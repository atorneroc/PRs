# Explicación: El modelo DORA y sus métricas

## ¿Qué es DORA?

DORA (DevOps Research and Assessment) es un programa de investigación que identificó cuatro métricas clave para medir el rendimiento de entrega de software de un equipo. Estas métricas fueron validadas a lo largo de más de 7 años de investigación por el equipo de Google Cloud.

Las métricas DORA miden dos dimensiones:

- **Velocidad** (throughput): qué tan rápido se entrega valor.
- **Estabilidad** (stability): qué tan confiable es lo que se entrega.

## Las 4 métricas

### Deployment Frequency (Velocidad)

Mide la frecuencia con la que el equipo despliega código a producción.

**Razonamiento**: equipos de alto rendimiento despliegan frecuentemente porque trabajan en lotes pequeños, lo que reduce riesgo y acelera el feedback.

**Operacionalización en este proyecto**: cada PR mergeado a `main` se cuenta como un despliegue. Esto asume que el merge a main dispara un despliegue automático o manual, que es el estándar de la industria para flujos GitFlow.

### Lead Time for Changes (Velocidad)

Mide el tiempo desde que un desarrollador hace su primer commit hasta que ese cambio está en producción.

**Razonamiento**: un lead time corto indica que el pipeline de entrega tiene poca fricción. Incluye tiempo de desarrollo, code review, QA y despliegue.

**Operacionalización en este proyecto**: se captura el flujo completo `feature → develop → qa → main`:

1. **Inicio**: primer commit exclusivo del feature branch (Compare API contra develop).
2. **Fin**: fecha de merge del PR a `main`.
3. **Cálculo**: diferencia en días.

Se elige la fecha del primer commit (no la creación del PR) porque refleja mejor cuándo se empezó a trabajar en el cambio.

### Change Failure Rate (Estabilidad)

Mide el porcentaje de despliegues a producción que resultan en un fallo que requiere intervención (hotfix, rollback o revert).

**Razonamiento**: una CFR baja indica que los procesos de calidad (code review, testing, QA) son efectivos. Una CFR alta sugiere que se están empujando cambios sin suficiente validación.

**Operacionalización en este proyecto**: se clasifican los PRs mergeados a `main` según su rama origen y título:

- Ramas que comienzan con `hotfix/`, `bugfix/`, `fix/`, `revert-` → fallo.
- Títulos que contienen "hotfix", "revert", "rollback" → fallo.

**Limitación conocida**: esta heurística depende de que el equipo siga convenciones de nomenclatura de ramas. Si un hotfix no sigue la convención, no se detectará.

### Mean Time to Recovery (Estabilidad)

Mide el tiempo promedio que tarda el equipo en recuperarse de un fallo en producción.

**Razonamiento**: fallos son inevitables. Lo que diferencia a los equipos de alto rendimiento es la velocidad de respuesta. Un MTTR bajo indica automatización, procesos claros de respuesta a incidentes y cultura de urgencia apropiada.

**Operacionalización en este proyecto**: para cada PR de hotfix/revert mergeado a `main`:

1. **Inicio del incidente**: fecha de creación del issue vinculado (si existe) o fecha de creación del PR.
2. **Resolución**: fecha del merge a `main`.
3. **Cálculo**: diferencia en horas.

Se prioriza la fecha del issue porque representa mejor cuándo se detectó el problema (antes de que se empezara a trabajar en la corrección).

## Clasificación de equipos DORA

| Métrica | Elite | High | Medium | Low |
|---|---|---|---|---|
| Deployment Frequency | Múltiples veces al día | Entre una vez al día y una vez a la semana | Entre una vez a la semana y una vez al mes | Más de 6 meses |
| Lead Time for Changes | Menos de 1 día | Entre 1 día y 1 semana | Entre 1 semana y 1 mes | Más de 6 meses |
| Change Failure Rate | 0%–15% | 16%–30% | 31%–45% | Mayor a 45% |
| Mean Time to Recovery | Menos de 1 hora | Menos de 1 día | Menos de 1 semana | Más de 6 meses |

## Relación entre velocidad y estabilidad

Un hallazgo clave de la investigación DORA es que **velocidad y estabilidad no están en conflicto**. Los equipos Elite son rápidos *y* estables. Esto se logra mediante:

- Integración continua y despliegue frecuente en lotes pequeños.
- Automatización de testing y validación.
- Trunk-based development o flujos con merge frecuente.
- Cultura de mejora continua basada en datos.

## Fuentes

- Forsgren, N., Humble, J., Kim, G. (2018). *Accelerate: The Science of Lean Software and DevOps*. IT Revolution Press.
- Google Cloud DORA: https://dora.dev
