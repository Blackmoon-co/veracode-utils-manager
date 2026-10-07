import argparse
import sys
from collections import Counter
from pathlib import Path
import pandas as pd
import requests
sys.path.append(str(Path(__file__).parent.parent))
from src.veracode_users_manager import VeracodeUsersManager
from src.veracode_teams_manager import VeracodeTeamsManager

REQUIRED_COLUMNS = ["email_address", "first_name", "last_name"]

# Doc Veracode: "Team membership affects only users with the Submitter and Reviewer roles".
# Con un rol ignore_team_restrictions (Administrator, Security Lead, Executive...) el team no hace falta.
TEAM_ROLES = {"extreviewer", "extsubmitter"}

# Perfil -> roles (obligatorios + opcionales de la matriz interna perfil->roles, todos incluidos).
# Nombres tal como aparecen en la UI de Veracode; se traducen a role_name con la API (role_description).
PROFILES = {
    "developer": ["Reviewer", "Submitter", "Greenlight IDE User", "Security Labs User", "Sandbox User"],
    "developer lead": ["Reviewer", "Submitter", "Workspace Editor", "Greenlight IDE User",
                       "Security Labs User", "Mitigation Approver", "Sandbox Administrator", "Sandbox User"],
    "technical lead": ["Reviewer", "Submitter", "Workspace Administrator", "Greenlight IDE User",
                       "Security Labs User", "Mitigation Approver", "Sandbox User"],
    "architect": ["Reviewer", "Workspace Editor", "Submitter", "Greenlight IDE User",
                 "Security Labs User", "Mitigation Approver", "Sandbox User"],
    "devops engineer": ["Delete Scans", "Sandbox Administrator", "Submitter", "Workspace Editor",
                        "Workspace Administrator", "Reviewer", "Creator"],
    "qa / release engineer": ["Reviewer"],
    "project manager / product owner": ["Security Insights", "Team Admin", "Reviewer"],
    "engineering leader": ["Reviewer", "Submitter", "Workspace Editor", "Greenlight IDE User",
                           "Security Labs User", "Mitigation Approver", "Sandbox User"],
    "application stakeholder": ["Executive"],
    "executive / management": ["Executive"],
    "appsec manager": ["Security Insights", "Creator", "Reviewer", "Delete Scans"],
    "security team member": ["Executive", "Mitigation Approver", "Policy Administrator", "Reviewer"],
    "security risk team": ["Policy Administrator", "Reviewer"],
    "security leader": ["Security Lead", "Executive", "Mitigation Approver", "Policy Administrator",
                        "Reviewer", "Delete Scans", "Workspace Administrator"],
    "vulnerability manager": ["Security Insights"],
    "account administrator": ["Administrator", "Creator", "Delete Scans", "Executive", "Policy Administrator", "Reviewer", "Sandbox Administrator", "Security Lead"],
}


def build_role_lookup(roles):
    """Permite referirse a un rol por role_name ('extreviewer') o por nombre de UI ('Reviewer')."""
    lookup = {}
    for role in roles:
        lookup[role["role_name"].lower()] = role["role_name"]
        if role.get("role_description"):
            lookup[role["role_description"].lower()] = role["role_name"]
    return lookup


def read_file(file_path):
    """Lee .xlsx o .csv y devuelve una lista de dicts con columnas normalizadas."""
    if file_path.lower().endswith(".xlsx"):
        df = pd.read_excel(file_path, dtype=str)
    elif file_path.lower().endswith(".csv"):
        df = pd.read_csv(file_path, dtype=str, encoding="utf-8-sig")
    else:
        raise ValueError("El archivo debe ser .csv o .xlsx")
    df.columns = df.columns.str.strip().str.replace('﻿', '').str.lower()
    df = df.fillna("")
    return [{k: v.strip() for k, v in row.items()} for row in df.to_dict(orient="records")]


def split_list(value):
    """'a; b;c' -> ['a', 'b', 'c']"""
    return [v.strip() for v in value.split(";") if v.strip()]


def build_users(rows, default_perfil, default_roles, role_lookup, team_ids_by_name):
    """Valida las filas y arma los parámetros de create_user. Devuelve (usuarios, errores).
    Roles = roles del perfil + roles extra; si la fila no trae ninguno se usan --perfil / --roles."""
    users, errors = [], []
    for i, row in enumerate(rows, start=2):  # fila 1 = encabezados
        missing = [c for c in REQUIRED_COLUMNS if not row.get(c)]
        if missing:
            errors.append(f"Fila {i}: faltan {', '.join(missing)}")
            continue

        perfil = row.get("perfil", "")
        extra_roles = split_list(row.get("roles", ""))
        if not perfil and not extra_roles:
            perfil, extra_roles = default_perfil, default_roles
        if perfil and perfil.lower() not in PROFILES:
            errors.append(f"Fila {i}: perfil desconocido '{perfil}'")
            continue
        wanted = (PROFILES[perfil.lower()] if perfil else []) + extra_roles
        if not wanted:
            errors.append(f"Fila {i}: sin roles (columna 'perfil'/'roles' o --perfil/--roles)")
            continue
        unknown_roles = [r for r in wanted if r.lower() not in role_lookup]
        if unknown_roles:
            errors.append(f"Fila {i}: roles inexistentes {unknown_roles}")
            continue
        roles = list(dict.fromkeys(role_lookup[r.lower()] for r in wanted))  # sin duplicados, en orden

        team_names = split_list(row.get("teams", ""))
        unknown_teams = [t for t in team_names if t not in team_ids_by_name]
        if unknown_teams:
            errors.append(f"Fila {i}: teams inexistentes {unknown_teams}")
            continue

        users.append({
            "user_name": row.get("user_name") or row["email_address"],
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "email_address": row["email_address"],
            "role_names": roles,
            "team_ids": [team_ids_by_name[t] for t in team_names],
        })
    return users, errors


def plan_user(user, existing, team_free_roles):
    """Decide qué hacer con un usuario ya validado. existing = detalle del usuario en Veracode o None.
    Si existe solo SUMA los roles y teams del archivo a los que ya tiene (nunca quita nada).
    Devuelve (accion, payload, mensaje); accion: 'crear', 'actualizar', 'sin cambios' o 'error'."""
    roles = [r["role_name"] for r in (existing or {}).get("roles") or []]
    new_roles = [r for r in user["role_names"] if r not in roles]
    roles += new_roles
    # team_id -> relationship (MEMBER/ADMIN). Team Admin administra los teams del archivo; un ADMIN nunca se baja
    current = {t["team_id"]: (t.get("relationship") or {}).get("name", "MEMBER")
               for t in (existing or {}).get("teams") or []}
    teams = dict(current)
    for t in user["team_ids"]:
        if teams.get(t) != "ADMIN":
            teams[t] = "ADMIN" if "teamAdmin" in roles else "MEMBER"
    changed_teams = [t for t in teams if current.get(t) != teams[t]]
    if existing and not new_roles and not changed_teams:
        return "sin cambios", None, "ya tiene todos los roles y teams del archivo"
    if not teams and TEAM_ROLES & set(roles) and not team_free_roles & set(roles):
        return "error", None, "Reviewer/Submitter exigen al menos un team: llenar la columna 'teams' (ver --list-teams)"
    if "teamAdmin" in roles and "ADMIN" not in teams.values():
        return "error", None, "Team Admin necesita en la columna 'teams' el team que va a administrar"
    team_objs = [{"team_id": t, "relationship": {"name": "ADMIN"}} if rel == "ADMIN" else {"team_id": t}
                 for t, rel in teams.items()]
    shown = [f"{t} ({rel})" for t, rel in teams.items()]
    if not existing:
        return "crear", dict(user, teams=team_objs), f"roles={roles} teams={shown}"
    payload = {"roles": [{"role_name": r} for r in roles], "teams": team_objs}
    return "actualizar", payload, f"agrega roles={new_roles} teams={[t for t in shown if t.split()[0] in changed_teams]}"


def main():
    parser = argparse.ArgumentParser(description="Crea o actualiza usuarios de Veracode desde un .xlsx o .csv")
    parser.add_argument("file", nargs="?", help="Ruta al archivo .xlsx o .csv")
    parser.add_argument("--perfil", default="Developer", help="Perfil por defecto si la fila no trae perfil ni roles (default: Developer)")
    parser.add_argument("--roles", default="", help="Roles extra por defecto separados por ';' (nombre UI o role_name)")
    parser.add_argument("--dry-run", action="store_true", help="Valida y muestra qué se crearía/actualizaría, sin escribir nada")
    parser.add_argument("--list-roles", action="store_true", help="Muestra los role_name disponibles y sale")
    parser.add_argument("--list-teams", action="store_true", help="Muestra los nombres de teams (para la columna teams) y sale")
    args = parser.parse_args()

    if args.list_teams:
        for team in sorted(VeracodeTeamsManager().list_all_teams(), key=lambda t: t["team_name"].lower()):
            print(team["team_name"])
        return

    users_manager = VeracodeUsersManager()
    try:
        roles = users_manager.list_roles()
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else None
        if status == 401:
            sys.exit("❌ Veracode no reconoce las credenciales de ~/.veracode/veracode.yml (401): el API ID/Key "
                     f"es inválido, expiró o fue regenerado.\n   Detalle: {e.response.text[:300]}")
        if status == 403:
            sys.exit("❌ Las credenciales de ~/.veracode/veracode.yml no tienen permiso (403). Para crear usuarios "
                     "se necesita un usuario con rol Administrator o un usuario API con rol 'Admin API'.")
        raise

    if args.list_roles:
        for role in roles:
            print(f"{role['role_name']:35} {role.get('role_description', '')}")
        return
    if not args.file:
        parser.error("falta la ruta del archivo")

    rows = read_file(args.file)
    team_ids_by_name = {}
    if any(row.get("teams") for row in rows):
        team_ids_by_name = {t["team_name"]: t["team_id"] for t in VeracodeTeamsManager().list_all_teams()}

    users, errors = build_users(
        rows, args.perfil, split_list(args.roles), build_role_lookup(roles), team_ids_by_name)

    # Si el user_name ya existe se actualiza, si no se crea. Todo se decide antes de escribir nada.
    print(f"Buscando {len(users)} usuario(s) en Veracode...")
    team_free_roles = {r["role_name"] for r in roles if r.get("ignore_team_restrictions")}
    plans = []
    for user in users:
        found = users_manager.find_user(user["user_name"])
        existing = users_manager.get_user(found["user_id"]) if found else None
        action, payload, msg = plan_user(user, existing, team_free_roles)
        if action == "error":
            errors.append(f"{user['email_address']}: {msg}")
        if existing and existing.get("active") is False:
            msg += " ⚠️ inactivo en Veracode (no se reactiva)"
        plans.append((user["email_address"], existing, action, payload, msg))

    # Todo o nada en la validación: si hay filas malas no se crea ni actualiza nadie
    if errors:
        print("❌ Errores de validación, no se creó ni actualizó ningún usuario:")
        for error in errors:
            print(f"   {error}")
        sys.exit(1)

    results = Counter()
    for email, existing, action, payload, msg in plans:
        if args.dry_run or action == "sin cambios":
            print(f"{'[dry-run] ' if args.dry_run else ''}{action} {email}: {msg}")
            results[action] += 1
            continue
        try:
            if action == "crear":
                new_user = users_manager.create_user(**payload)
                print(f"✅ Creado {email} (ID: {new_user.get('user_id')}): {msg}")
            else:
                users_manager.update_user(existing["user_id"], payload)
                print(f"✅ Actualizado {email}: {msg}")
            results[action] += 1
        except Exception as e:
            detail = getattr(getattr(e, "response", None), "text", "")
            print(f"❌ Error al {action} '{email}': {e} {detail}")
            results["error"] += 1

    print(f"\n{'[dry-run] ' if args.dry_run else ''}{len(plans)} usuario(s): "
          + ", ".join(f"{action}={n}" for action, n in results.items()))


if __name__ == "__main__":
    main()
