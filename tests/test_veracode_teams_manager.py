import unittest
from unittest.mock import patch, MagicMock
import os
import yaml
from src.veracode_teams_manager import VeracodeTeamsManager

class TestVeracodeTeamsManager(unittest.TestCase):

    @patch('src.veracode_teams_manager.RequestsAuthPluginVeracodeHMAC')
    @patch('src.veracode_teams_manager.os.path.exists')
    @patch('src.veracode_teams_manager.open', new_callable=unittest.mock.mock_open, read_data=yaml.dump({
        'api': {
            'key-id': 'test-key-id',
            'key-secret': 'test-key-secret'
        }
    }))
    def setUp(self, mock_open, mock_exists, mock_auth):
        mock_exists.return_value = True
        self.manager = VeracodeTeamsManager()

    @patch('src.veracode_teams_manager.requests.request')
    def test_list_teams(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {'teams': [{'id': '1', 'name': 'Team 1'}]}
        mock_request.return_value = mock_response

        teams = self.manager.list_teams()

        self.assertEqual(teams, {'teams': [{'id': '1', 'name': 'Team 1'}]})
        mock_request.assert_called_once_with(
            'GET',
            'https://api.veracode.com/api/authn/v2/teams',
            auth=self.manager.auth,
            headers=self.manager.headers,
            json=None
        )

    @patch('src.veracode_teams_manager.requests.request')
    def test_create_team(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {'id': '2', 'name': 'New Team'}
        mock_request.return_value = mock_response

        new_team = self.manager.create_team('New Team')

        self.assertEqual(new_team, {'id': '2', 'name': 'New Team'})
        mock_request.assert_called_once_with(
            'POST',
            'https://api.veracode.com/api/authn/v2/teams',
            auth=self.manager.auth,
            headers=self.manager.headers,
            json={'team_name': 'New Team'}
        )

    # Aquí puedes agregar más tests para get_team, update_team, delete_team, etc.

if __name__ == '__main__':
    unittest.main()