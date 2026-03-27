# Guía: Configurar el token de GitHub

Esta guía explica las opciones de autenticación disponibles y por qué el workflow usa una GitHub App.

## Configuración actual

El workflow usa una **GitHub App** mediante el job `generate-token`. Esto requiere los secrets `APP_ID` y `APP_PRIVATE_KEY`. Para instrucciones de configuración, consulta la [guía de setup de GitHub App](setup-github-app.md).

## Opciones de token

### Opción 1: GitHub App (configuración actual)

La opción usada en el workflow. Ofrece:

- **Rate-limit superior**: 5,000 requests/hora base, escalable hasta 15,000 con organizaciones de 20+ usuarios (+50/usuario).
- **Permisos granulares**: solo los necesarios, sin acceso total a la cuenta del usuario.
- **Token auto-renovable**: se genera automáticamente en cada ejecución del workflow.
- **Auditoría**: los requests aparecen como la app, no como un usuario personal.

**Permisos necesarios para la GitHub App:**

| Permiso | Nivel | Motivo |
|---|---|---|
| Repository: Pull requests | Read | Leer PRs y sus commits |
| Repository: Contents | Read | Comparar ramas (Compare API) |
| Repository: Metadata | Read | Listar repos de la org |
| Repository: Issues | Read | Timeline API para MTTR |
| Organization: Members | Read | Listar repos de la org |

### Opción 2: Fine-grained Personal Access Token

Alternativa para ejecución local o si no puedes crear una GitHub App.

- **Rate-limit**: 5,000 requests por hora.
- **Permisos granulares**: seleccionas exactamente qué repos y qué permisos.
- **Expiración configurable**: define una fecha de expiración (obligatoria).

**Pasos para crear uno:**

1. Ve a **GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens**.
2. Selecciona **Generate new token**.
3. Configura:
   - **Resource owner**: tu organización (`CCAPITAL-APPS`)
   - **Repository access**: All repositories (o selecciona los que tengan el topic)
   - **Permissions**:
     - Pull requests: Read
     - Contents: Read
     - Metadata: Read
     - Issues: Read
4. Selecciona **Generate token**.
5. Copia el token para usarlo como `GH_TOKEN` en ejecución local.

### Opción 3: Token clásico (no recomendada)

- **Rate-limit**: 5,000 requests por hora.
- **Permisos**: `repo` (acceso total a todos los repos del usuario).
- **Riesgo**: acceso excesivamente amplio, sin granularidad.

Si ya usas un token clásico, el scope mínimo necesario es `repo`.

## Comparativa

| Característica | Token clásico | Fine-grained PAT | GitHub App |
|---|---|---|---|
| Rate-limit | 5,000/h | 5,000/h | 5,000–15,000/h |
| Permisos granulares | No | Sí | Sí |
| Expiración obligatoria | No | Sí | Auto-renovable |
| Auditoría | Usuario | Usuario | App dedicada |
| Configuración | Baja | Media | Alta (una vez) |
| Uso en workflow | Manual (secret) | Manual (secret) | Automático (generate-token) |

## Recomendación

1. **GitHub App** para el workflow de Actions (configuración actual).
2. **Fine-grained PAT** para ejecución local o testing.
3. **Token clásico** solo como último recurso temporal.

## Referencia adicional

- [Documentación de rate-limits de GitHub](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
- [Crear una GitHub App](https://docs.github.com/en/apps/creating-github-apps)
- [Fine-grained PAT](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#fine-grained-personal-access-tokens)
