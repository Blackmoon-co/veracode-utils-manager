import unittest
from src.create_users_from_file import build_users, build_role_lookup, plan_user, split_list

ROLE_LOOKUP = build_role_lookup([
    {"role_name": "extsubmitter", "role_description": "Submitter"},
    {"role_name": "extreviewer", "role_description": "Reviewer"},
    {"role_name": "teamAdmin", "role_description": "Team Admin"},
    {"role_name": "workSpaceEditor", "role_description": "Workspace Editor"},
    {"role_name": "greenlightideuser", "role_description": "Greenlight IDE User"},
    {"role_name": "securitylabsuser", "role_description": "Security Labs User"},
    {"role_name": "sandboxuser", "role_description": "Sandbox User"},
    {"role_name": "mitigationapprover", "role_description": "Mitigation Approver"},
    {"role_name": "sandboxadmin", "role_description": "Sandbox Administrator"},
])
DEVELOPER_ROLES = ["extreviewer", "extsubmitter", "greenlightideuser", "securitylabsuser", "sandboxuser"]
TEAMS = {"Backend": "t-1", "QA": "t-2"}


def row(**overrides):
    base = {"email_address": "ana@x.com", "first_name": "Ana", "last_name": "Diaz",
            "perfil": "", "roles": "", "teams": ""}
    base.update(overrides)
    return base


def build(rows, perfil="", roles=None):
    return build_users(rows, perfil, roles or [], ROLE_LOOKUP, TEAMS)


class TestBuildUsers(unittest.TestCase):

    def test_split_list(self):
        self.assertEqual(split_list(" a; b;;c "), ["a", "b", "c"])

    def test_perfil_developer_con_teams(self):
        users, errors = build([row(perfil="Developer", teams="Backend; QA")])
        self.assertEqual(errors, [])
        self.assertEqual(users[0]["user_name"], "ana@x.com")
        self.assertEqual(users[0]["role_names"], DEVELOPER_ROLES)
        self.assertEqual(users[0]["team_ids"], ["t-1", "t-2"])

    def test_perfil_mas_roles_opcionales_sin_duplicados(self):
        users, _ = build([row(perfil="developer lead", roles="Submitter;extreviewer")])
        self.assertEqual(users[0]["role_names"], ["extreviewer", "extsubmitter", "teamAdmin", "workSpaceEditor",
                                                   "greenlightideuser", "securitylabsuser",
                                                   "mitigationapprover", "sandboxadmin", "sandboxuser"])

    def test_defaults_solo_si_la_fila_no_trae_nada(self):
        users, _ = build([row(), row(roles="Submitter")], perfil="Developer")
        self.assertEqual(users[0]["role_names"], DEVELOPER_ROLES)
        self.assertEqual(users[1]["role_names"], ["extsubmitter"])

    def test_validation_errors(self):
        rows = [row(email_address=""), row(perfil="Astronauta"), row(roles="noexiste"),
                row(perfil="Developer", teams="Fantasma"), row()]
        users, errors = build(rows)
        self.assertEqual(users, [])
        self.assertEqual(len(errors), 5)
        self.assertIn("Fila 2: faltan email_address", errors[0])
        self.assertIn("perfil desconocido", errors[1])


TEAM_FREE = {"extseclead"}
USER = {"user_name": "ana@x.com", "first_name": "Ana", "last_name": "Diaz", "email_address": "ana@x.com",
        "role_names": ["extreviewer", "sandboxuser"], "team_ids": []}


def existing(roles, teams):
    return {"user_id": "u-1", "roles": [{"role_name": r} for r in roles], "teams": [{"team_id": t} for t in teams]}


class TestPlanUser(unittest.TestCase):

    def test_nuevo_con_team_se_crea(self):
        action, payload, _ = plan_user(dict(USER, team_ids=["t-1"]), None, TEAM_FREE)
        self.assertEqual(action, "crear")
        self.assertEqual(payload["team_ids"], ["t-1"])

    def test_nuevo_sin_team_con_reviewer_es_error(self):
        self.assertEqual(plan_user(USER, None, TEAM_FREE)[0], "error")

    def test_rol_sin_restriccion_de_team_no_exige_team(self):
        self.assertEqual(plan_user(dict(USER, role_names=["extseclead", "extreviewer"]), None, TEAM_FREE)[0], "crear")

    def test_existente_suma_roles_y_teams_sin_quitar_nada(self):
        action, payload, _ = plan_user(dict(USER, team_ids=["t-2"]),
                                       existing(["extadmin", "extreviewer"], ["t-1"]), TEAM_FREE)
        self.assertEqual(action, "actualizar")
        self.assertEqual(payload, {
            "roles": [{"role_name": "extadmin"}, {"role_name": "extreviewer"}, {"role_name": "sandboxuser"}],
            "teams": [{"team_id": "t-1"}, {"team_id": "t-2"}]})

    def test_existente_conserva_sus_teams_si_el_archivo_no_trae(self):
        action, payload, _ = plan_user(USER, existing(["extreviewer"], ["t-1"]), TEAM_FREE)
        self.assertEqual(action, "actualizar")
        self.assertEqual(payload["teams"], [{"team_id": "t-1"}])

    def test_existente_sin_teams_y_con_reviewer_es_error(self):
        self.assertEqual(plan_user(USER, existing(["sandboxuser"], []), TEAM_FREE)[0], "error")

    def test_team_admin_nuevo_administra_sus_teams(self):
        action, payload, _ = plan_user(dict(USER, role_names=["extreviewer", "teamAdmin"], team_ids=["t-1"]),
                                       None, TEAM_FREE)
        self.assertEqual(action, "crear")
        self.assertEqual(payload["teams"], [{"team_id": "t-1", "relationship": {"name": "ADMIN"}}])

    def test_team_admin_sin_team_es_error(self):
        user = dict(USER, role_names=["extseclead", "teamAdmin"])
        self.assertIn("Team Admin", plan_user(user, None, TEAM_FREE)[2])

    def test_actualizar_no_baja_un_admin_a_member(self):
        current = {"user_id": "u-1", "roles": [{"role_name": "teamAdmin"}],
                   "teams": [{"team_id": "t-1", "relationship": {"name": "ADMIN"}}]}
        action, payload, _ = plan_user(dict(USER, team_ids=["t-1"]), current, TEAM_FREE)
        self.assertEqual(action, "actualizar")
        self.assertEqual(payload["teams"], [{"team_id": "t-1", "relationship": {"name": "ADMIN"}}])

    def test_existente_sin_cambios(self):
        self.assertEqual(plan_user(USER, existing(["extreviewer", "sandboxuser"], ["t-1"]), TEAM_FREE)[0],
                         "sin cambios")


if __name__ == '__main__':
    unittest.main()
