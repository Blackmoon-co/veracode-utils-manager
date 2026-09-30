import unittest
from unittest.mock import patch, mock_open
from io import StringIO
from src.create_teams_from_csv import create_teams_from_csv

class TestCreateTeamsFromCSV(unittest.TestCase):

    @patch('src.create_teams_from_csv.VeracodeTeamsManager')
    def test_create_teams_from_csv(self, mock_manager):
        csv_content = "team_name\nTeam 1\nTeam 2\nTeam 3"
        mock_manager_instance = mock_manager.return_value
        mock_manager_instance.create_team.side_effect = [
            {'team_id': '1', 'team_name': 'Team 1'},
            {'team_id': '2', 'team_name': 'Team 2'},
            {'team_id': '3', 'team_name': 'Team 3'}
        ]

        with patch('builtins.open', mock_open(read_data=csv_content)):
            create_teams_from_csv('dummy_path.csv')

        self.assertEqual(mock_manager_instance.create_team.call_count, 3)
        mock_manager_instance.create_team.assert_any_call('Team 1')
        mock_manager_instance.create_team.assert_any_call('Team 2')
        mock_manager_instance.create_team.assert_any_call('Team 3')

    @patch('src.create_teams_from_csv.VeracodeTeamsManager')
    def test_create_teams_from_csv_with_error(self, mock_manager):
        csv_content = "team_name\nTeam 1\nTeam 2\nTeam 3"
        mock_manager_instance = mock_manager.return_value
        mock_manager_instance.create_team.side_effect = [
            {'team_id': '1', 'team_name': 'Team 1'},
            Exception("API Error"),
            {'team_id': '3', 'team_name': 'Team 3'}
        ]

        with patch('builtins.open', mock_open(read_data=csv_content)):
            with patch('builtins.print') as mock_print:
                create_teams_from_csv('dummy_path.csv')

        self.assertEqual(mock_manager_instance.create_team.call_count, 3)
        mock_print.assert_any_call("Error al crear el equipo 'Team 2': API Error")

if __name__ == '__main__':
    unittest.main()