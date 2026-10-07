# CLAUDE.md

Utilidades en Python (y algunos PowerShell) para administrar una organización Veracode vía REST API: **Teams**, **Users** y **Applications** (perfiles de aplicación), con cargas masivas desde CSV/XLSX. Idioma del código, mensajes y docs: **español**.

## Estructura

```
veracode-utils-master/
├── apps.csv / apps.xlsx            # Datos de entrada de apps (ojo: apps.csv es en realidad un XLSX renombrado, binario)
└── veracode-teams-manager/         # Único paquete real; trabajar SIEMPRE con cwd aquí
    ├── src/
    │   ├── veracode_teams_manager.py        # VeracodeTeamsManager    -> /api/authn/v2 (teams)
    │   ├── veracode_users_manager.py        # VeracodeUsersManager    -> /api/authn/v2 (users)
    │   ├── veracode_applications_manager.py # VeracodeApplicationsManager -> /appsec/v1 (applications)
    │   ├── create_teams_from_csv.py         # CLI: crea teams desde CSV (columna team_name)
    │   ├── create_applications_from_csv.py  # CLI: crea apps desde CSV o XLSX (usa pandas)
    │   ├── create_users_from_file.py        # CLI: crea usuarios desde CSV o XLSX (con --dry-run)
    │   └── __main__.py                      # `python -m src <csv>` -> crea teams (import roto, ver abajo)
    ├── tests/                               # unittest + mocks, sin llamadas reales a la API
    ├── data/teams_example.csv
    ├── apps.xlsx                            # Entrada de ejemplo/real para create_applications
    ├── get-teams.ps1                        # Firma HMAC manual en PowerShell, GET teams
    ├── get-veracode-teams.ps1               # Función Get-VeracodeTeams (incompleta)
    ├── pipeline-scan.yml                    # Azure DevOps: build .NET -> Pipeline Scan SAST -> Flaw Importer
    ├── setup.py / requirements.txt
    └── README.md
```

## Patrón de los managers

Las tres clases `Veracode*Manager` son copias del mismo esqueleto:

- `__init__(api_key_id=None, api_key_secret=None)`: si no se pasan credenciales, `load_credentials()` lee `~/.veracode/veracode.yml`:
  ```yaml
  api:
      key-id: ...
      key-secret: ...
  ```
  Lanza `FileNotFoundError` / `ValueError` si falta el archivo o las claves.
- Auth: `RequestsAuthPluginVeracodeHMAC` (paquete `veracode-api-signing`).
- `_make_request(method, endpoint, data=None[, params])` → `requests.request(...)`, `raise_for_status()`, devuelve `response.json()`.
- `base_url` fijo a la región comercial US: `https://api.veracode.com/...` (EU sería `api.veracode.eu`).
- Cada módulo tiene un bloque `if __name__ == "__main__":` usado como "playground" manual con mucho código comentado. **El de `veracode_applications_manager.py` CREA una aplicación real al ejecutarse** — no correrlo a ciegas.

Si se agrega un endpoint, seguir el mismo patrón (método delgado sobre `_make_request`). `load_credentials` está triplicado; si se toca en uno, tocar los tres (o extraerlo a un módulo común).

### Endpoints implementados

| Clase | Método | HTTP |
|---|---|---|
| Teams | `list_teams`, `get_team`, `create_team`, `update_team`, `delete_team` | `GET/POST/PUT/DELETE teams[/{id}]` |
| Teams | `update_team_user(team_id, user_id)` | `PUT teams/{id}/users/{user_id}` (no verificado contra la doc oficial) |
| Teams | `list_all_teams(page_size=500)` | `GET teams?all_for_org=true` paginado |
| Users | `get_users`, `get_user`, `create_user`, `find_user(user_name)` (exacto, sin distinguir mayúsculas) | `users[/{id}]`, `GET users?user_name=` |
| Users | `update_user(user_id, data)` | `PUT users/{id}?partial=true` (`roles`/`teams` reemplazan la lista completa) |
| Users | `list_roles()` | `GET roles?size=500` |
| Apps | `list_applications` (1 página), `list_all_applications(page_size=100)` (paginado `page`/`size`, resultado en `_embedded.applications`) | `GET applications` |
| Apps | `get_application`, `create_application`, `delete_application` | `applications[/{guid}]` |
| Apps | `get_applications_by_business_unit(bu_guid)` | filtra en cliente sobre `list_all_applications` |
| Apps | `update_application`, `update_application_policy` | ver "Problemas conocidos" |

`create_application` arma `{"profile": {name, description, policies:[{guid}], business_criticality, business_unit:{guid}}}`. El parámetro `policies` es **un solo GUID** de política pese al plural. `business_criticality` válidos: `VERY_HIGH, HIGH, MEDIUM, LOW, VERY_LOW`.

## Scripts de carga masiva

Ejecutar desde `veracode-teams-manager/` (los scripts hacen `sys.path.append(parent.parent)` e importan `from src.xxx import ...`):

```bash
python src/create_teams_from_csv.py data/teams_example.csv
python src/create_applications_from_csv.py apps.xlsx     # o .csv
```

- **Teams**: CSV UTF-8 con columna `team_name`.
- **Users** (`create_users_from_file.py`, .xlsx o .csv): columnas `email_address`, `first_name`, `last_name` obligatorias; `user_name` (default = email), `perfil`, `roles` y `teams` opcionales, varios valores separados por `;`. `perfil` (ej. `Developer`, `Developer Lead`, `DevOps Engineer`…) se expande con el dict `PROFILES` (incluye roles obligatorios + opcionales de la matriz interna perfil→roles; `roles` es para extras fuera de la matriz). Los roles se aceptan por nombre de UI (`Reviewer`) o `role_name` (`extreviewer`); `build_role_lookup` los traduce usando `role_description` de `GET roles`. `teams` usa nombres (se resuelven a `team_id` con `list_all_teams`). Flags: `--list-roles`, `--list-teams`, `--perfil X` (default `Developer` = Reviewer + Submitter + Greenlight IDE User + Security Labs User + Sandbox User) y `--roles "a;b"` (defaults si la fila no trae perfil ni roles), `--dry-run`. Si el `user_name` ya existe lo actualiza (`plan_user`: SUMA roles/teams del archivo a los que tiene, nunca quita); si no, lo crea. Reviewer/Submitter sin ningún team (y sin rol `ignore_team_restrictions`) es error de validación. Valida todo contra la API antes de escribir; si algo falla no crea ni actualiza ninguno. Plantilla: `data/desarrolladores_plantilla.xlsx`.
  ```bash
  python src/create_users_from_file.py --list-roles
  python src/create_users_from_file.py --list-teams
  python src/create_users_from_file.py data/desarrolladores_plantilla.xlsx --dry-run
  ```
- **Applications**: columnas `application_name`, `description`, `policy` (GUID), `business_criticality`, `business_unit_guid`. Los encabezados se normalizan (trim, minúsculas, quita BOM, `aplication_name` → `application_name`). Filas con cualquier campo vacío se saltan con advertencia; errores por fila se imprimen y se continúa (no hay rollback ni detección de duplicados).

## Comandos

```bash
cd veracode-teams-manager
pip install -r requirements.txt
python -m unittest discover tests
```

Los tests parchean `src.<modulo>.requests.request`, `open`, `os.path.exists` y `RequestsAuthPluginVeracodeHMAC`; cubren Teams, `create_teams_from_csv` y la validación de `create_users_from_file` (`build_users` y `plan_user`, funciones puras) y `find_user`/`update_user`. Al agregar tests, mantener ese estilo (unittest + `unittest.mock`, sin red).

## Problemas conocidos (no asumir que funcionan)

- **Seguridad:** `get-teams.ps1` tiene un API ID/Key de Veracode hardcodeados. Nunca copiar ni reutilizar esos valores; las credenciales van en `~/.veracode/veracode.yml` o variables de entorno/secretos del pipeline.
- `setup.py` no declara `pandas` ni `openpyxl` (sí están en `requirements.txt`).
- `setup.py` usa `package_dir={"": "src"}` y el entry point `create-teams=create_teams_from_csv:main`, pero los módulos importan `from src....`; el paquete instalado (`pip install -e .` / `create-teams`) probablemente no funciona. Usar los scripts directamente.
- `src/__main__.py` hace `from create_teams_from_csv import ...` (sin `src.`), así que `python -m src` falla salvo que `src/` esté en el path.
- `update_application` manda `{"application_name": ...}`; la API appsec v1 espera el objeto `profile` completo en el PUT. `update_application_policy` usa `PUT applications/{guid}/policies`, endpoint no documentado. Para cambiar nombre/política: GET del perfil, modificar `profile` y PUT `applications/{guid}` con el perfil completo.
- `get_applications_by_business_unit` crea una nueva instancia del manager internamente en vez de usar `self`.
- `list_all_applications` traga excepciones por página y devuelve resultados parciales.
- `get-veracode-teams.ps1` llama `Get-HmacAuthorizationHeader`, que no está definida en ningún archivo.
- `.gitignore` excluye `*.csv` y `*.json` (incluye `data/teams_example.csv`).
- `apps.csv` en la raíz no es CSV: es un XLSX con extensión cambiada; `pd.read_csv` fallará sobre él.

## Pipeline (`pipeline-scan.yml`)

Azure DevOps, 3 jobs: `Build` (Windows, NuGet + VSBuild, empaqueta el `.zip` en `app_to_scan.zip`) → `SAST_Scan` (Ubuntu, descarga `pipeline-scan.jar`, falla en severidad `Very High,High`, pero `|| true` hace que nunca rompa el build) → `Import_Results` (tarea `Veracode Flaw Importer@3` crea work items). Variables secretas esperadas: `VERACODE_API_ID`, `VERACODE_API_KEY`, `VERACODE_SCA_TOKEN`. App de ejemplo: `verademo-net`.

## Convenciones

- Python ≥ 3.9, sin type hints salvo en `normalize_columns`; mensajes a consola en español, a veces con emojis ✅/❌.
- Salida vía `print`, sin logging.
- No hay git en este directorio; no hay linter/formatter configurado.
- Cualquier acción de escritura (`create_*`, `update_*`, `delete_*`) impacta la organización Veracode real: confirmar con el usuario antes de ejecutar scripts contra la API.
