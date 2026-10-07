import os
import yaml
import requests
from veracode_api_signing.plugin_requests import RequestsAuthPluginVeracodeHMAC

class VeracodeUsersManager:
    def __init__(self, api_key_id=None, api_key_secret=None):
        self.base_url = "https://api.veracode.com/api/authn/v2"
        self.headers = {"Content-Type": "application/json"}

        if api_key_id is None or api_key_secret is None:
            api_key_id, api_key_secret = self.load_credentials()

        self.auth = RequestsAuthPluginVeracodeHMAC(api_key_id, api_key_secret)


    def load_credentials(self):
            
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

    def _make_request(self, method, endpoint, data=None, params=None):
        url = f"{self.base_url}/{endpoint}"
        response = requests.request(
            method,
            url,
            auth=self.auth,
            headers=self.headers,
            json=data,
            params=params
        )
        response.raise_for_status()
        return response.json()

    def get_users(self):
        return self._make_request("GET", "users")

    def get_user(self, user_id):
        return self._make_request("GET", f"users/{user_id}")

    def list_roles(self):
        """Lista los roles disponibles (role_name, role_description)."""
        # ponytail: una sola página de 500, Veracode tiene ~50 roles
        response = self._make_request("GET", "roles", params={"size": 500})
        return response.get("_embedded", {}).get("roles", [])

    def create_user(self, user_name, first_name, last_name, email_address, role_names, team_ids=None, teams=None):
        """Crea un usuario humano. role_names: lista de role_name; team_ids: lista de team_id
        (o teams: lista de objetos team ya armados, p.ej. con relationship ADMIN para Team Admin)."""
        data = {
            "user_name": user_name,
            "first_name": first_name,
            "last_name": last_name,
            "email_address": email_address,
            "active": True,
            "roles": [{"role_name": r} for r in role_names],
        }
        if teams:
            data["teams"] = teams
        elif team_ids:
            data["teams"] = [{"team_id": t} for t in team_ids]

        return self._make_request("POST", "users", data)
    
    def find_user(self, user_name):
        """Busca por user_name exacto (la API no distingue mayúsculas). Devuelve el resumen o None."""
        response = self._make_request("GET", "users", params={"user_name": user_name})
        users = response.get("_embedded", {}).get("users", [])
        # Se re-filtra en cliente: si la API ignorara el filtro, nunca se toca a otro usuario
        return next((u for u in users if u["user_name"].lower() == user_name.lower()), None)

    def update_user(self, user_id, data):
        """PUT parcial: solo cambia los campos enviados. Ojo: 'roles' y 'teams' reemplazan la lista completa."""
        return self._make_request("PUT", f"users/{user_id}", data, params={"partial": "true"})
    
if __name__ == "__main__":
    try:

        manager = VeracodeUsersManager()

        # Solo lectura: muestra los role_name válidos para usar en create_user
        for role in manager.list_roles():
            print(f"{role['role_name']:35} {role.get('role_description', '')}")

        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Asegúrate de tener un archivo veracode.yml en el directorio .veracode de tu directorio home.")
    except ValueError as e:
        print(f"Error: {e}")
        print("Verifica que tu archivo veracode.yml contenga las claves api.key-id y api.key-secret.")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")