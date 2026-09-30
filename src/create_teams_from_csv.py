import csv
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from src.veracode_teams_manager import VeracodeTeamsManager

def create_teams_from_csv(csv_file_path):
    manager = VeracodeTeamsManager()
    
    with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            team_name = row.get('team_name')
            if not team_name:
                print(f"Advertencia: Fila sin nombre de equipo: {row}")
                continue
            
            try:
                new_team = manager.create_team(team_name)
                print(f"Equipo creado: {team_name} (ID: {new_team['team_id']})")
            except Exception as e:
                print(f"Error al crear el equipo '{team_name}': {str(e)}")

def main():
    if len(sys.argv) != 2:
        print("Uso: python create_teams.py <ruta_archivo_csv>")
        sys.exit(1)
    
    csv_file_path = sys.argv[1]
    
    try:
        create_teams_from_csv(csv_file_path)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo CSV en {csv_file_path}")
    except Exception as e:
        print(f"Error inesperado: {str(e)}")

if __name__ == "__main__":
    main()