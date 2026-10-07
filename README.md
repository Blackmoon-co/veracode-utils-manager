# Veracode Utils Manager

Utilidades en Python para administrar una organización Veracode vía REST API: **Teams**, **Users** y **Applications** (perfiles de aplicación), con cargas masivas desde CSV/XLSX.

> ⚠️ Cualquier script `create_*` / `update_*` / `delete_*` escribe contra la organización Veracode real. Revisar el archivo de entrada (`--dry-run` cuando esté disponible) antes de correrlo.

## Estructura

```
├── src/
│   ├── veracode_teams_manager.py        # VeracodeTeamsManager    -> /api/authn/v2 (teams)
│   ├── veracode_users_manager.py        # VeracodeUsersManager    -> /api/authn/v2 (users)
│   ├── veracode_applications_manager.py # VeracodeApplicationsManager -> /appsec/v1 (applications)
│   ├── create_teams_from_csv.py         # CLI: crea teams desde CSV
│   ├── create_applications_from_csv.py  # CLI: crea apps desde CSV o XLSX
│   ├── create_users_from_file.py        # CLI: crea usuarios desde CSV o XLSX (con --dry-run)
│   └── __main__.py
├── tests/                               # unittest + mocks, sin llamadas reales a la API
├── data/
│   ├── teams_example.csv
│   ├── users_example.csv
│   ├── apps.xlsx / apps.csv             # apps.csv es en realidad un XLSX renombrado (binario)
│   └── desarrolladores_plantilla.xlsx   # plantilla para carga de usuarios (ver más abajo)
├── get-teams.ps1 / get-veracode-teams.ps1
└── setup.py / requirements.txt
```

## Instalación

```bash
pip install -r requirements.txt
```

> `pip install -e .` / el entry point `create-teams` no funcionan (ver [Problemas conocidos](#problemas-conocidos)). Usar los scripts directamente con `python src/...`.

## Configuración de credenciales

Cada manager, si no recibe `api_key_id` / `api_key_secret` por parámetro, lee `~/.veracode/veracode.yml`:

```yaml
api:
    key-id: tu_api_key_id
    key-secret: tu_api_key_secret
```

Sin ese archivo (o con claves faltantes) los managers lanzan `FileNotFoundError` / `ValueError`. Región fija: comercial US (`api.veracode.com`).

## Los tres managers

Las clases `Veracode*Manager` comparten el mismo esqueleto: autenticación HMAC (`RequestsAuthPluginVeracodeHMAC`), un método `_make_request(method, endpoint, data=None, params=None)` que hace la llamada y `raise_for_status()`, y devuelven JSON.

| Clase | Métodos | Endpoint |
|---|---|---|
| `VeracodeTeamsManager` | `list_teams`, `get_team`, `create_team`, `update_team`, `delete_team`, `update_team_user`, `list_all_teams(page_size=500)` | `teams[/{id}]` |
| `VeracodeUsersManager` | `get_users`, `get_user`, `find_user(user_name)`, `create_user`, `update_user(user_id, data)` (PUT `?partial=true`), `list_roles()` | `users[/{id}]`, `roles` |
| `VeracodeApplicationsManager` | `list_applications`, `list_all_applications(page_size=100)`, `get_application`, `create_application`, `delete_application`, `get_applications_by_business_unit`, `update_application`, `update_application_policy` | `applications[/{guid}]` |

`create_application` espera `policies` como un solo GUID de política (pese al plural) y `business_criticality` en `VERY_HIGH, HIGH, MEDIUM, LOW, VERY_LOW`.

## Carga masiva de Teams

CSV UTF-8 con columna `team_name`:

```bash
python src/create_teams_from_csv.py data/teams_example.csv
```

## Carga masiva de Applications

CSV o XLSX con columnas `application_name`, `description`, `policy` (GUID), `business_criticality`, `business_unit_guid`. Encabezados se normalizan (trim, minúsculas, sin BOM). Filas con algún campo vacío se saltan con advertencia; errores por fila se imprimen y se continúa con el resto (no hay rollback ni detección de duplicados).

```bash
python src/create_applications_from_csv.py data/apps.xlsx     # o data/apps.csv
```

## Carga masiva de Usuarios

```bash
python src/create_users_from_file.py --list-roles                              # roles disponibles en la org
python src/create_users_from_file.py --list-teams                              # teams disponibles (para la columna teams)
python src/create_users_from_file.py data/desarrolladores_plantilla.xlsx --dry-run
python src/create_users_from_file.py data/desarrolladores_plantilla.xlsx       # crea / actualiza de verdad
```

- Si el `user_name` **ya existe** en Veracode, se **actualiza**: se le **suman** los roles y teams del archivo a los que ya tiene (nunca se quita nada). Si ya los tiene todos: `sin cambios`. Si el usuario está inactivo se avisa, pero no se reactiva.
- Si **no existe**, se **crea**.
- Reviewer y Submitter exigen al menos un team (salvo que el usuario tenga Administrator, Security Lead, Executive u otro rol con `ignore_team_restrictions`). Si el usuario nuevo no trae `teams`, o el existente no tiene ninguno, es error de validación.
- Valida **todas** las filas contra la API antes de escribir: si una falla, no se crea ni actualiza ningún usuario.

### Columnas del archivo (.xlsx o .csv)

| Columna | Obligatoria | Descripción |
|---|---|---|
| `email_address` | sí | Email del usuario |
| `first_name` | sí | Nombre |
| `last_name` | sí | Apellido |
| `user_name` | no | Default: `email_address` |
| `perfil` | no* | Nombre de perfil (tabla de abajo) → expande a su lista de roles |
| `roles` | no* | Roles extra, separados por `;`. Se acepta el nombre de UI (`Reviewer`) o el `role_name` interno (`extreviewer`) |
| `teams` | no | Nombres de team separados por `;` (se resuelven a `team_id`) |

\* Si una fila no trae `perfil` ni `roles`, se usan los defaults `--perfil` (default `Developer`) / `--roles`. `perfil` y `roles` se **combinan** (roles del perfil + roles extra), sin duplicados — ver ejemplo de `carlos.ruiz` en la plantilla.

### Perfiles disponibles (`PROFILES` en `create_users_from_file.py`)

| Perfil | Roles asignados |
|---|---|
| Developer | Reviewer, Submitter, Greenlight IDE User, Security Labs User, Sandbox User |
| Developer Lead | Reviewer, Submitter, Team Admin, Workspace Editor, Greenlight IDE User, Security Labs User, Mitigation Approver, Sandbox Administrator, Sandbox User |
| Technical Lead | Reviewer, Submitter, Workspace Administrator, Greenlight IDE User, Security Labs User, Mitigation Approver, Sandbox User |
| Architect | Reviewer, Workspace Editor, Submitter, Greenlight IDE User, Security Labs User, Mitigation Approver, Sandbox User |
| DevOps Engineer | Delete Scans, Sandbox Administrator, Submitter, Workspace Editor, Workspace Administrator, Reviewer, Creator |
| QA / Release Engineer | Reviewer |
| Project Manager / Product Owner | Security Insights, Team Admin, Reviewer |
| Engineering Leader | Reviewer, Submitter, Workspace Editor, Greenlight IDE User, Security Labs User, Mitigation Approver, Sandbox User |
| Application Stakeholder | Executive |
| Executive / Management | Executive |
| AppSec Manager | Security Insights, Creator, Reviewer, Delete Scans |
| Security Team Member | Executive, Mitigation Approver, Policy Administrator, Reviewer |
| Security Risk Team | Policy Administrator, Reviewer |
| Security Leader | Security Lead, Executive, Mitigation Approver, Policy Administrator, Reviewer, Delete Scans, Workspace Administrator |
| Vulnerability Manager | Security Insights |
| Account Administrator | Administrator, Creator, Delete Scans, Executive, Policy Administrator, Reviewer, Sandbox Administrator, Security Lead |

Esta tabla también está en la hoja **"Perfiles"** de `data/desarrolladores_plantilla.xlsx`, generada directamente desde `PROFILES` — si se toca el dict en el código, regenerar la hoja para que no quede desactualizada.

### Plantilla `data/desarrolladores_plantilla.xlsx`

Hoja **"Usuarios"**: columnas `email_address`, `first_name`, `last_name`, `perfil`, `roles`, `teams`, con dropdown nativo de Excel en `perfil` (lista de los 16 perfiles válidos, evita typos). Filas de ejemplo mostrando los distintos casos de uso: perfil solo, perfil + rol extra, y solo `roles` manuales sin perfil.

Hoja **"Perfiles"**: tabla de referencia (perfil → roles incluidos), la misma de arriba.

### Flags

- `--perfil X` — perfil default para filas sin `perfil` ni `roles` (default: `Developer`)
- `--roles "a;b"` — roles extra default para esas mismas filas
- `--dry-run` — valida y muestra qué se crearía / actualizaría, sin escribir nada (sí hace GETs para buscar usuarios)
- `--list-roles`, `--list-teams`

## Tests

```bash
python -m unittest discover tests
```

Los tests parchean `requests.request`, `open`, `os.path.exists` y `RequestsAuthPluginVeracodeHMAC`; no hacen llamadas de red. Cubren Teams, `create_teams_from_csv`, `build_users` y `plan_user` (funciones puras de `create_users_from_file`) y `find_user`/`update_user`.

## Problemas conocidos

- **Seguridad:** `get-teams.ps1` tiene un API ID/Key de Veracode hardcodeados. No reutilizar esos valores; las credenciales van en `~/.veracode/veracode.yml` o secretos del pipeline.
- `setup.py` no declara `pandas` ni `openpyxl` (sí están en `requirements.txt`), y su entry point (`create-teams`) probablemente no funciona porque los módulos importan `from src....` — usar los scripts directamente.
- `src/__main__.py` hace `from create_teams_from_csv import ...` (sin `src.`), así que `python -m src` falla salvo que `src/` esté en el path.
- `update_application` manda `{"application_name": ...}`, pero la API appsec v1 espera el objeto `profile` completo en el PUT. Para cambiar nombre/política: GET del perfil, modificar `profile` y PUT `applications/{guid}` con el perfil completo. `update_application_policy` usa un endpoint no documentado.
- `get_applications_by_business_unit` crea una instancia nueva del manager en vez de usar `self`.
- `list_all_applications` traga excepciones por página y devuelve resultados parciales.
- `get-veracode-teams.ps1` llama a `Get-HmacAuthorizationHeader`, no definida en ningún archivo.
- `data/apps.csv` no es CSV real: es un XLSX con la extensión cambiada; `pd.read_csv` falla sobre él.
- El bloque `if __name__ == "__main__":` de `veracode_applications_manager.py` **crea una aplicación real** al ejecutarse — no correrlo a ciegas.
