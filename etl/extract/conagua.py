import requests
import os
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

stations = [31078, 31095, 31044, 31097, 31036]

base_url = "https://smn.conagua.gob.mx/tools/RESOURCES/Normales_Climatologicas/Diarios/yuc/"
folder = "data/raw"

os.makedirs(folder, exist_ok=True)

for station in stations:
    url = f"{base_url}dia{station}.txt"

    try:
        response = requests.get(url, verify=False, timeout=25)

        if response.status_code == 200:
            file_path = os.path.join(folder, f"conagua_{station}.txt")

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(response.text)

            print(f"Guardado: {file_path}")

        else:
            print(f"Error HTTP {response.status_code} en estación {station}")

    except Exception as e:
        print(f"Error en estación {station}: {e}")