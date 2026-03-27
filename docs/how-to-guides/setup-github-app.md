# Guía: Configurar GitHub App Token en el workflow

El workflow usa una GitHub App para autenticarse contra la API. El job `generate-token` crea un token temporal en cada ejecución.

## Paso 1: Obtener los datos de tu GitHub App

1. Ve a **GitHub Settings → Developer settings → GitHub Apps**
2. Selecciona tu app
3. Copia estos valores:
   - **App ID**: número que ves en la página principal
   - **Private Key**: descarga o copia desde "Private keys"

### Permisos necesarios

| Permiso | Nivel | Motivo |
|---|---|---|
| Repository: Pull requests | Read | Leer PRs y sus commits |
| Repository: Contents | Read | Comparar ramas (Compare API) |
| Repository: Metadata | Read | Listar repos de la org |
| Repository: Issues | Read | Timeline API para MTTR |
| Organization: Members | Read | Listar repos de la org |

## Paso 2: Guardar como secrets en el repositorio

1. En tu repositorio, ve a **Settings → Secrets and variables → Actions**
2. Crea **2 nuevos secrets**:

### Secret 1: `APP_ID`
- Nombre: `APP_ID`
- Valor: el número de tu app (ej: `123456`)
- Selecciona **Add secret**

### Secret 2: `APP_PRIVATE_KEY`
- Nombre: `APP_PRIVATE_KEY`
- Valor: copia **TODO** el contenido de la private key (incluye `-----BEGIN RSA PRIVATE KEY-----` y `-----END RSA PRIVATE KEY-----`)
- Selecciona **Add secret**

## Paso 3: Ejecutar el workflow

1. Ve a **Actions → DORA Metrics**
2. Selecciona **Run workflow**
3. Configura los parámetros (organización, topic, rango de fechas opcional)
4. Selecciona **Run workflow**

El primer job (`generate-token`) generará un token temporal válido para esa ejecución. Los demás jobs lo reciben automáticamente como `GH_TOKEN`.

## Cómo funciona internamente

```yaml
generate-token:
  runs-on: ubuntu-latest
  outputs:
    token: ${{ steps.app-token.outputs.token }}
  steps:
    - name: Generar token de GitHub App
      id: app-token
      uses: actions/create-github-app-token@v1
      with:
        app-id: ${{ secrets.APP_ID }}
        private-key: ${{ secrets.APP_PRIVATE_KEY }}
        owner: ${{ github.event.inputs.org }}
```

Los jobs de métricas consumen el token así:

```yaml
env:
  GH_TOKEN: ${{ needs.generate-token.outputs.token }}
```

## Ventajas

- **Rate-limit de 10,000–15,000 req/h** (según el número de usuarios de la org)
- **Token auto-renovable** (no expira)
- **Permisos granulares** (solo lectura sobre los recursos necesarios)
- **Auditoría clara** (los requests aparecen como la app, no como un usuario)

## Troubleshooting

### Error: "App not installed on this repository"
- Asegúrate de que la GitHub App está instalada en toda la **organización**, no solo en el repo donde corre el workflow.
- Ve a **GitHub Settings → Applications → Installed GitHub Apps**.

### Error: "Invalid app-id or private-key"
- Verifica que los secrets se crearon correctamente.
- Asegúrate de que la private key incluye las líneas `-----BEGIN` y `-----END`.

### Error: "RateLimitExceeded"
- Aumenta `SHARDS` en el workflow (de 10 a 20).
- O reduce `max-parallel` de 3 a 2 para espaciar los requests.

## Ejecución local

La GitHub App no funciona localmente. Para testing local, usa un **Fine-grained PAT**:

```bash
export GH_TOKEN="github_pat_xxxxx..."
export GH_ORG="CCAPITAL-APPS"
export GH_TOPIC="tribu-canal-digital"
export SHARDS=10
export SHARD_ID=1

python scripts/deployment_frequency.py
```
