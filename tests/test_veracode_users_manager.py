import unittest
from unittest.mock import patch
from src.veracode_users_manager import VeracodeUsersManager


@patch('src.veracode_users_manager.requests.request')
class TestVeracodeUsersManager(unittest.TestCase):

    @patch('src.veracode_users_manager.RequestsAuthPluginVeracodeHMAC')
    def setUp(self, mock_auth):
        self.manager = VeracodeUsersManager('test-key-id', 'test-key-secret')

    def test_find_user_sin_distinguir_mayusculas(self, mock_request):
        mock_request.return_value.json.return_value = {
            "_embedded": {"users": [{"user_name": "ana@x.com", "user_id": "u-1"}]}}
        self.assertEqual(self.manager.find_user("ANA@x.com")["user_id"], "u-1")
        self.assertEqual(mock_request.call_args.kwargs["params"], {"user_name": "ANA@x.com"})

    def test_find_user_nunca_devuelve_otro_usuario(self, mock_request):
        mock_request.return_value.json.return_value = {
            "_embedded": {"users": [{"user_name": "otro@x.com", "user_id": "u-9"}]}}
        self.assertIsNone(self.manager.find_user("ana@x.com"))

    def test_find_user_sin_resultados(self, mock_request):
        mock_request.return_value.json.return_value = {"page": {"total_elements": 0}}
        self.assertIsNone(self.manager.find_user("ana@x.com"))

    def test_update_user_es_parcial(self, mock_request):
        self.manager.update_user("u-1", {"roles": [{"role_name": "extreviewer"}]})
        mock_request.assert_called_once_with(
            "PUT", "https://api.veracode.com/api/authn/v2/users/u-1",
            auth=self.manager.auth, headers=self.manager.headers,
            json={"roles": [{"role_name": "extreviewer"}]}, params={"partial": "true"})


if __name__ == '__main__':
    unittest.main()
