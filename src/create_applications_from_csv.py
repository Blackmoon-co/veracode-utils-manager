import csv
import sys
from pathlib import Path
import pandas as pd   # 👈 necesario para leer .xlsx
sys.path.append(str(Path(__file__).parent.parent))
from src.veracode_applications_manager import VeracodeApplicationsManager

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza nombres de columnas:
    - Quita espacios
    - Convierte a minúsculas
    - Elimina BOM (\ufeff)
    - Corrige nombres mal escritos como 'aplication_name'
    """
    df.columns = (
        df.columns.str.strip()
        .str.replace('\ufeff', '', regex=True)
        .str.lower()
    )
    df.rename(columns={
        "aplication_name": "application_name",  # corrige error de escritura
    }, inplace=True)
    return df

def create_applications_from_file(file_path):
    manager = VeracodeApplicationsManager()
    rows = []

    # Detecta si es .xlsx o .csv
    if file_path.lower().endswith(".xlsx"):
        try:
            df = pd.read_excel(file_path)
            df = normalize_columns(df)
            rows = df.to_dict(orient="records")
        except Exception as e:
            print(f"Error al leer el archivo Excel {file_path}: {e}")
            return
    elif file_path.lower().endswith(".csv"):
        try:
            df = pd.read_csv(file_path, encoding="utf-8")
            df = normalize_columns(df)
            rows = df.to_dict(orient="records")
        except Exception as e:
            print(f"Error al leer el archivo CSV {file_path}: {e}")
            return
    else:
        print("Error: El archivo debe ser .csv o .xlsx")
        return

    # Procesa las filas
    for row in rows:        
        application_name = row.get('application_name')
        if not application_name:
            print(f"Advertencia: Fila sin nombre de aplicacion: {row}")
            continue
        
        description = row.get('description')
        if not description:
            print(f"Advertencia: Fila sin description de aplicacion: {row}")
            continue
            
        policies = row.get('policy')
        if not policies:
            print(f"Advertencia: Fila sin policies de aplicacion: {row}")
            continue
        
        business_criticality = row.get('business_criticality')
        if not business_criticality:
            print(f"Advertencia: Fila sin business_criticality de aplicacion: {row}")
            continue

        business_unit_guid = row.get('business_unit_guid')
        if not business_unit_guid:
            print(f"Advertencia: Fila sin business_unit_guid de aplicacion: {row}")
            continue

        try:
            new_application = manager.create_application(
                application_name=application_name,
                description=description,
                business_criticality=business_criticality,
                policies=policies,
                business_unit_guid=business_unit_guid
            )
            print(f"✅ Aplicacion creada: {application_name} (ID: {new_application['guid']})")
        except Exception as e:
            print(f"❌ Error al crear la aplicacion '{application_name}': {str(e)}")

def main():
    if len(sys.argv) != 2:
        print("Uso: python create_applications.py <ruta_archivo_csv_o_xlsx>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    try:
        create_applications_from_file(file_path)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo en {file_path}")
    except Exception as e:
        print(f"Error inesperado: {str(e)}")

if __name__ == "__main__":
    main()
