import sys
from create_teams_from_csv import create_teams_from_csv

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python -m src <ruta_archivo_csv>")
        sys.exit(1)
    
    csv_file_path = sys.argv[1]
    create_teams_from_csv(csv_file_path)