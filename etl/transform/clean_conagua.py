import pandas as pd
import os
import re
from io import StringIO

input_folder = "data/raw"
output_folder = "data/processed"
os.makedirs(output_folder, exist_ok=True)

def dms_to_decimal(values):
    """Convierte grados/minutos/segundos a decimal"""
    if len(values) == 3:
        return values[0] + values[1] / 60 + values[2] / 3600
    elif len(values) == 2:
        return values[0] + values[1] / 60
    return values[0]

for file in os.listdir(input_folder):
    if file.endswith(".txt"):
        file_path = os.path.join(input_folder, file)
        
        with open(file_path, "r", encoding="latin-1") as f: # Latin-1 suele ser mejor para archivos Conagua
            lines = f.readlines()

        lat, lon = None, None
        start_line = 0

        for i, line in enumerate(lines):
            if "LATITUD" in line.upper():
                nums = list(map(float, re.findall(r"[-+]?\d*\.\d+|\d+", line)))
                lat = dms_to_decimal(nums)
            if "LONGITUD" in line.upper():
                nums = list(map(float, re.findall(r"[-+]?\d*\.\d+|\d+", line)))
                lon = -abs(dms_to_decimal(nums)) # Asegurar negativo para México (Oeste)
            if "FECHA" in line or "ANIO" in line or "AÑO" in line:
                start_line = i

        # Extraer datos tabulares
        data_lines = [lines[start_line].strip()] # Header
        for line in lines[start_line + 1:]:
            line_clean = line.strip()
            if re.match(r"^\d+", line_clean): # Solo líneas que empiecen con números (fechas)
                data_lines.append(line_clean)

        df = pd.read_csv(StringIO("\n".join(data_lines)), sep=r"\s+", engine="python")
        
        # Estandarizar nombres de columnas inmediatamente
        rename_map = {
            "fecha": "date", "anio": "year", "mes": "month", "dia": "day",
            "tmax": "temp_max", "tmin": "temp_min", "precip": "precipitation"
        }
        df.columns = [col.lower() for col in df.columns]
        df = df.rename(columns=rename_map)

        # Agregar metadatos
        df["latitud"] = lat
        df["longitud"] = lon
        df["station"] = file.replace(".txt", "")

        output_path = os.path.join(output_folder, file.replace(".txt", ".csv"))
        df.to_csv(output_path, index=False)
        print(f"✅ Procesado: {file}")