import pandas as pd
import requests
import os

def get_tfl_traffic_sensors():
    """
    Obtiene la ubicación y estado actual de los sensores de tráfico (TICs).
    Útil para el RQ5 (Representación Geográfica).
    """
    # Nota: Para peticiones masivas TfL recomienda registrarse y usar una API Key.
    # Esta es la URL de acceso público para sensores.
    url = "https://api.tfl.gov.uk/Place/Type/ElectronicTrafficSensor"

    params = {}
    app_key = os.getenv("TFL_APP_KEY")
    if app_key:
        params["app_key"] = app_key

    try:
        response = requests.get(url, params=params, timeout=30)
    except requests.RequestException as exc:
        print(f"Error de red al conectar con TfL: {exc}")
        return pd.DataFrame()

    if response.status_code == 200:
        data = response.json()

        # Aplanamos el JSON para obtener latitud y longitud
        sensors = []
        for place in data:
            sensors.append({
                'id': place['id'],
                'nombre': place['commonName'],
                'lat': place['lat'],
                'lon': place['lon']
            })

        return pd.DataFrame(sensors)
    else:
        print(f"Error al conectar con TfL: HTTP {response.status_code}")
        print(response.text[:1000])
        return pd.DataFrame()

df_sensores = get_tfl_traffic_sensors()
if df_sensores.empty:
    print("No se han podido obtener sensores de TfL.")
else:
    print(df_sensores.head())
    print(f"Sensores obtenidos: {len(df_sensores)}")
