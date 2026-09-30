import unittest
from src.create_users_from_file import build_users, build_role_lookup, split_list

ROLE_LOOKUP = build_role_lookup([
    {"role_name": "extsubmitter", "role_description": "Submitter"},
    {"role_name": "extreviewer", "role_description": "Reviewer"},
    {"role_name": "teamAdmin", "role_description": "Team Admin"},
    {"role_name": "workSpaceEditor", "role_description": "Workspace Editor"},
    {"role_name": "greenlightideuser", "role_description": "Greenlight IDE User"},
    {"role_name": "extelearn", "role_description": "eLearning"},
    {"role_name": "securitylabsuser", "role_description": "Security Labs User"},
    {"role_name": "sandboxuser", "role_description": "Sandbox User"},
    {"role_name": "mitigationapprover", "role_description": "Mitigation Approver"},
    {"role_name": "sandboxadmin", "role_description": "Sandbox Administrator"},
])
DEVELOPER_ROLES = ["extreviewer", "extsubmitter", "greenlightideuser", "extelearn", "securitylabsuser", "sandboxuser"]
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
                                                   "greenlightideuser", "extelearn", "securitylabsuser",
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


if __name__ == '__main__':
    unittest.main()
