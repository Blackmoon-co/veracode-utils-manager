import argparse
import sys
from pathlib import Path
import pandas as pd
import requests
sys.path.append(str(Path(__file__).parent.parent))
from src.veracode_users_manager import VeracodeUsersManager
from src.veracode_teams_manager import VeracodeTeamsManager

REQUIRED_COLUMNS = ["email_address", "first_name", "last_name"]

# Perfil -> roles (obligatorios + opcionales de la matriz interna perfil->roles, todos incluidos).
# Nombres tal como aparecen en la UI de Veracode; se traducen a role_name con la API (role_description).
PROFILES = {
    "developer": ["Reviewer", "Submitter", "Greenlight IDE User", "eLearning", "Security Labs User", "Sandbox User"],
    "developer lead": ["Reviewer", "Submitter", "Team Admin", "Workspace Editor", "Greenlight IDE User", "eLearning",
                       "Security Labs User", "Mitigation Approver", "Sandbox Administrator", "Sandbox User"],
    "technical lead": ["Reviewer", "Submitter", "Workspace Administrator", "Greenlight IDE User", "eLearning",
                       "Security Labs User", "Mitigation Approver", "Sandbox User"],
    "architect": ["Reviewer", "Workspace Editor", "Submitter", "Greenlight IDE User", "eLearning",
                 "Security Labs User", "Mitigation Approver", "Sandbox User"],
    "devops engineer": ["Delete Scans", "Sandbox Administrator", "Submitter", "Workspace Editor",
                        "Workspace Administrator", "Reviewer", "Creator"],
    "qa / release engineer": ["Reviewer"],
    "project manager / product owner": ["Security Insights", "Team Admin", "Reviewer"],
    "engineering leader": ["Reviewer", "Submitter", "Workspace Editor", "Greenlight IDE User", "eLearning",
                           "Security Labs User", "Mitigation Approver", "Sandbox User"],
    "application stakeholder": ["Executive"],
    "executive / management": ["Executive", "eLearning"],
    "appsec manager": ["Security Insights", "Creator", "Reviewer", "Delete Scans"],
    "security team member": ["Executive", "Mitigation Approver", "Policy Administrator", "Reviewer"],
    "security risk team": ["Policy Administrator", "Reviewer", "eLearning"],
    "security leader": ["Security Lead", "Executive", "Mitigation Approver", "Policy Administrator",
                        "Reviewer", "Delete Scans", "Workspace Administrator"],
    "vulnerability manager": ["Security Insights"],
    "account administrator": ["Administrator", "Creator", "Delete Scans", "Executive", "Policy Administrator",
                              "eLearning", "Reviewer", "Sandbox Administrator", "Security Lead"],
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


def main():
    parser = argparse.ArgumentParser(description="Crea usuarios de Veracode desde un .xlsx o .csv")
    parser.add_argument("file", nargs="?", help="Ruta al archivo .xlsx o .csv")
    parser.add_argument("--perfil", default="Developer", help="Perfil por defecto si la fila no trae perfil ni roles (default: Developer)")
    parser.add_argument("--roles", default="", help="Roles extra por defecto separados por ';' (nombre UI o role_name)")
    parser.add_argument("--dry-run", action="store_true", help="Valida y muestra lo que se crearía, sin crear nada")
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

    # Todo o nada en la validación: si hay filas malas no se crea nadie
    if errors:
        print("❌ Errores de validación, no se creó ningún usuario:")
        for error in errors:
            print(f"   {error}")
        sys.exit(1)

    for user in users:
        if args.dry_run:
            print(f"[dry-run] {user['email_address']} roles={user['role_names']} teams={user['team_ids']}")
            continue
        try:
            new_user = users_manager.create_user(**user)
            print(f"✅ Usuario creado: {user['email_address']} (ID: {new_user.get('user_id')})")
        except Exception as e:
            detail = getattr(getattr(e, "response", None), "text", "")
            print(f"❌ Error al crear '{user['email_address']}': {e} {detail}")

    print(f"\n{len(users)} usuario(s) {'validados (dry-run)' if args.dry_run else 'procesados'}")


if __name__ == "__main__":
    main()
