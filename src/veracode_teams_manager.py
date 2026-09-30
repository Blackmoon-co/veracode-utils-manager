import os
import yaml
import requests
from veracode_api_signing.plugin_requests import RequestsAuthPluginVeracodeHMAC

class VeracodeTeamsManager:
    def __init__(self, api_key_id=None, api_key_secret=None):
        self.base_url = "https://api.veracode.com/api/authn/v2"
        self.headers = {"Content-Type": "application/json"}
        
        if api_key_id is None or api_key_secret is None:
            api_key_id, api_key_secret = self.load_credentials()
        
        self.auth = RequestsAuthPluginVeracodeHMAC(api_key_id, api_key_secret)

    def load_credentials(self):
        """Carga las credenciales desde el archivo veracode.yml"""
        home = os.path.expanduser("~")
        config_file = os.path.join(home, '.veracode', 'veracode.yml')
        
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"No se encontró el archivo de configuración en {config_file}")
        
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        
        api = config.get('api', {})
        api_key_id = api.get('key-id')
        api_key_secret = api.get('key-secret')
        
        if not api_key_id or not api_key_secret:
            raise ValueError("No se encontraron credenciales válidas en el archivo de configuración")
        
        return api_key_id, api_key_secret

    def _make_request(self, method, endpoint, data=None):
        url = f"{self.base_url}/{endpoint}"
        response = requests.request(
            method,
            url,
            auth=self.auth,
            headers=self.headers,
            json=data
        )
        response.raise_for_status()
        return response.json()

    def list_teams(self):
        """Lista todos los Teams."""
        return self._make_request("GET", "teams")

    def list_all_teams(self, page_size=500):
        """Lista todos los Teams de la organización recorriendo todas las páginas."""
        teams, page = [], 0
        while True:
            response = self._make_request(
                "GET", f"teams?all_for_org=true&page={page}&size={page_size}")
            teams += response.get("_embedded", {}).get("teams", [])
            page += 1
            if page >= response.get("page", {}).get("total_pages", 0):
                return teams

    def get_team(self, team_id):
        """Consulta un Team específico por su ID."""
        return self._make_request("GET", f"teams/{team_id}")

    def create_team(self, team_name):
        """Crea un nuevo Team."""
        data = {"team_name": team_name}
        return self._make_request("POST", "teams", data)

    def update_team(self, team_id, new_team_name):
        """Edita un Team existente."""
        data = {"team_name": new_team_name}
        return self._make_request("PUT", f"teams/{team_id}", data)

    def delete_team(self, team_id):
        """Elimina un Team."""
        return self._make_request("DELETE", f"teams/{team_id}")
    
    def update_team_user(self, team_id, user_id):
        """Asigna team a un usuario."""
        data = {"team_id": team_id}
        return self._make_request("PUT", f"teams/{team_id}/users/{user_id}", data)

# Ejemplo de uso:
if __name__ == "__main__":
    try:
        # Ahora podemos crear una instancia sin proporcionar credenciales explícitamente
        manager = VeracodeTeamsManager()
        
        # Listar todos los Teams
        teams = manager.list_teams()
        print("Teams:", teams)
    
        
     #   user_details = manager.get_user("1234567890")
      #  print("User details:", user_details)
        
        # Crear un nuevo Team
        #new_team = manager.create_team("Nuevo Equipo")
        #print("Nuevo Team creado:", new_team)
        
        # Obtener detalles de un Team
        #team_details = manager.get_team(new_team['team_id'])
        #print("Detalles del Team:", team_details)
        
        # Actualizar un Team
        #updated_team = manager.update_team(new_team['team_id'], "Equipo Actualizado")
        #print("Team actualizado:", updated_team)
        
        # Eliminar un Team
        #manager.delete_team(new_team['team_id'])
        #print("Team eliminado")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Asegúrate de tener un archivo veracode.yml en el directorio .veracode de tu directorio home.")
    except ValueError as e:
        print(f"Error: {e}")
        print("Verifica que tu archivo veracode.yml contenga las claves api.key-id y api.key-secret.")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")