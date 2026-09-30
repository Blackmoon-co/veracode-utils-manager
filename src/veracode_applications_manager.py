import os
import yaml
import requests
import json
from veracode_api_signing.plugin_requests import RequestsAuthPluginVeracodeHMAC

class VeracodeApplicationsManager:
    def __init__(self, api_key_id=None, api_key_secret=None):
        self.base_url = "https://api.veracode.com/appsec/v1"
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
    
    def list_all_applications(self, page_size=100):
        """Lista TODAS las aplicaciones manejando paginación"""
        all_applications = []
        page = 0
        
        while True:
            try:
                print(f"Obteniendo página {page}...")
                
                # Hacer request con parámetros de paginación
                params = {
                    'page': page,
                    'size': page_size
                }
                
                response = self._make_request("GET", "applications", params=params)
                applications = response['_embedded']['applications']
                
                if not applications:
                    break
                
                all_applications.extend(applications)
                print(f"Obtenidas {len(applications)} aplicaciones en página {page}")
                
                # Verificar si hay más páginas
                if len(applications) < page_size:
                    break
                
                page += 1
                
            except Exception as e:
                print(f"Error en página {page}: {e}")
                break
        
        self.all_applications = all_applications
        return all_applications

    def list_applications(self):
        """Lista todos las Aplicaciones."""
        return self._make_request("GET", "applications")

    def get_application(self, application_id):
        """Consulta un application específico por su ID."""
        return self._make_request("GET", f"applications/{application_id}")

    def create_application(self, application_name, description, policies, business_criticality, business_unit_guid):
        """Crea un nuevo application."""
        data = {
            "profile": {
              "name": application_name,
              "description": description,
              "policies": [
                {
                  "guid": policies
                }
              ],
              "business_criticality": business_criticality,
              "business_unit": {
                "guid": business_unit_guid
              }
            }
          }     
        print(f'Data: {data}')
        return self._make_request("POST", "applications", data)

    def update_application(self, application_id, new_application_name):
        """Edita un application existente."""
        data = {"application_name": new_application_name}
        return self._make_request("PUT", f"applications/{application_id}", data)

    def delete_application(self, application_id):
        """Elimina un application."""
        return self._make_request("DELETE", f"applications/{application_id}")
    
    def get_applications_by_business_unit(self, business_unit_guid):
        applications = []
        """Obtiene aplicaciones por unidad de negocio."""
        manager = VeracodeApplicationsManager()
   
        all_apps = manager.list_all_applications()
        for app in all_apps:
            profile = app['profile']
            if 'business_unit' in profile and profile['business_unit']['guid'] == business_unit_guid:
                applications.append(app)
        self.applications = applications
        return applications

    def update_application_policy(self, application_id, new_policy_guid):
        """Actualiza la política de una aplicación."""
        data = {
            "policies": [
                {
                    "guid": new_policy_guid
                }
            ]
        }
        return self._make_request("PUT", f"applications/{application_id}/policies", data)
# Ejemplo de uso:
if __name__ == "__main__":
    try:
        # Ahora podemos crear una instancia sin proporcionar credenciales explícitamente
        manager = VeracodeApplicationsManager()
        #bad8b000-c48c-4626-a018-118a10783429
        #cbfa7b0e-27a5-4909-90da-5d0cee2432ba
     #   print("Obteniendo aplicaciones por unidad de negocio...")
    #    apps_by_business = manager.get_applications_by_business_unit("bad8b000-c48c-4626-a018-118a10783429")
     #   print(f"Total apps found: {len(apps_by_business)}")
     #   for app in apps_by_business:
     #       policy = app['profile']['policies'][0]
     #       business_unit = app['profile'].get('business_unit', {})
     #       print(f"guid: {app['guid']}, app_name: {app['profile']['name']},policy_guid:{policy['guid']}, policy: {policy['name']}, business_unit: {business_unit.get('name', 'N/A')}")
    #        application = manager.get_application(app['guid'])
     #       response = manager.update_application_policy(app['guid'], "cbfa7b0e-27a5-4909-90da-5d0cee2432ba")
     #       print(response)
            
      #  all_apps = manager.list_all_applications()
     
      #  print(f"Total de aplicaciones obtenidas: {len(all_apps)}")
        
      #  for idx, app in enumerate(all_apps, 1):
      #      profile = app.get('profile', {})
      #      policies = profile.get('policies', [])
      #      print(f"\n")
      #      print(f"Nombre:{profile.get('name', 'Sin nombre')}")
      #      print(f"   GUID: {app.get('guid')}")
      #      print(f"   Criticidad de Negocio: {profile.get('business_criticality', 'N/A')}")
      #      print(f"   Politica: {policies[0].get('name', 'Sin nombre')}")
        
      #  for application in apps:
      #      print(f"\nNombre: {application['profile']['name']}")
        
        # Crear un nuevo application
        new_application = manager.create_application(
            application_name="Nueva Aplicacion",
           description="una descripcion",
           business_criticality="HIGH",
            policies="e6fbed91-c596-4921-a33a-71b5882d9671",
            business_unit_guid="23c78f2a-873d-477b-bf57-74cbb7c1daac"
            )
        print("Nuevo application creado:", new_application)
        
        # Obtener detalles de un application
        #application_details = manager.get_application(new_application['application_id'])
        #print("Detalles del application:", application_details)
        
        # Actualizar un application
        #updated_application = manager.update_application(new_application['application_id'], "Equipo Actualizado")
        #print("application actualizado:", updated_application)
        
        # Eliminar un application
        #manager.delete_application(new_application['application_id'])
        #print("application eliminado")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Asegúrate de tener un archivo veracode.yml en el directorio .veracode de tu directorio home.")
    except ValueError as e:
        print(f"Error: {e}")
        print("Verifica que tu archivo veracode.yml contenga las claves api.key-id y api.key-secret.")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")