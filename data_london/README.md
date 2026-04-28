# Data London

Conjunto base de datos oficiales para implementar el trabajo final sobre Londres.

## Estructura

- `raw/laqn/`
  Series horarias descargadas desde London Air Quality Network.
- `raw/tfl/`
  Ficheros de TfL: estaciones, GTFS y limite ULEZ.
- `metadata/laqn_sites.csv`
  Metadatos de las estaciones de calidad del aire seleccionadas.
- `metadata/laqn_download_manifest.csv`
  Registro de los CSV descargados y sus URLs oficiales.
- `metadata/tfl_stops.csv`
  Export completo de `stops.txt` del GTFS de TfL.
- `metadata/tfl_geo_stops.csv`
  Version filtrada con solo paradas que tienen latitud y longitud.

## Fuentes oficiales

- LAQN API y descargas:
  - <https://www.londonair.org.uk/LondonAir/API/>
  - <https://www.londonair.org.uk/london/asp/datadownload.asp>
- TfL open data:
  - <https://tfl.gov.uk/info-for/open-data-users/our-open-data>

## Cobertura de requisitos

- `RQ1 - Ciudad real`
  - Se cubre con el caso de estudio de Londres usando fuentes oficiales publicas.
  - Datos implicados:
    - series LAQN de calidad del aire
    - estaciones y paradas de TfL
    - limite geografico ULEZ

- `RQ2 - Integracion de dos areas del curso`
  - `Sostenibilidad ambiental`
    - `raw/laqn/MY1/no2_pm25_o3_2019_2024.csv`
    - `raw/laqn/KC1/no2_pm25_o3_2019_2024.csv`
    - `raw/laqn/WM6/no2_pm25_o3_2019_2024.csv`
  - `Movilidad urbana`
    - `metadata/tfl_geo_stops.csv`
    - `raw/tfl/tfl_stationdata_gtfs/`
    - `raw/tfl/stations.kml`

- `RQ3 - Dashboard interactivo`
  - Se puede construir con los datos ya descargados.
  - Componentes recomendados:
    - KPIs de contaminacion
    - mapas de sensores y paradas
    - series temporales de NO2
    - comparativas espaciales con ULEZ
    - resultados del modelo predictivo

- `RQ4 - Analisis tecnico`
  - La opcion recomendada es `series temporales`.
  - Datos implicados:
    - series horarias LAQN
    - `metadata/laqn_sites.csv`
  - Analisis posibles:
    - patrones por hora y dia
    - medias moviles
    - comparativa entre estaciones
    - prediccion de NO2
  - Extra opcional:
    - analisis de red/proximidad con `tfl_geo_stops.csv`

- `RQ5 - Representacion geografica`
  - Se cubre con mapas de sensores, transporte y frontera ULEZ.
  - Datos implicados:
    - `metadata/laqn_sites.csv`
    - `metadata/tfl_geo_stops.csv`
    - `raw/tfl/ulez_boundary/LEZ.shp`
    - `raw/tfl/stations.kml`

## Estaciones LAQN incluidas

- `MY1` - Westminster - Marylebone Road
- `KC1` - Kensington and Chelsea - North Kensington
- `WM6` - Westminster - Oxford Street
- `CT3` - Camden - Bloomsbury
- `BX1` - Bexley - Belvedere West

## Descarga / refresco

Ejecuta:

```bash
./.venv/bin/python scripts/download_london_data.py
```

## Uso recomendado en el notebook

- Variable objetivo principal: `NO2`
- Variables secundarias: `PM25`, `O3`
- Representacion geografica:
  - `raw/tfl/stations.kml`
  - `raw/tfl/ulez_boundary/`
- Movilidad:
  - `metadata/tfl_geo_stops.csv`
  - `raw/tfl/tfl_stationdata_gtfs/`

## Archivos recomendados para empezar ya

- Aire:
  - `raw/laqn/MY1/no2_pm25_o3_2019_2024.csv`
  - `raw/laqn/KC1/no2_pm25_o3_2019_2024.csv`
  - `raw/laqn/WM6/no2_pm25_o3_2019_2024.csv`
- Sensores y metadatos:
  - `metadata/laqn_sites.csv`
- Movilidad:
  - `metadata/tfl_geo_stops.csv`
- Geografia:
  - `raw/tfl/ulez_boundary/LEZ.shp`
  - `raw/tfl/stations.kml`

## Siguiente paso

Construir una tabla maestra por estacion y timestamp con:

- contaminante
- valor
- coordenadas del sensor
- distancia a estacion TfL mas cercana
- indicador dentro/fuera del limite ULEZ

## Hace falta descargar mas datos?

No es necesario para cumplir el trabajo.

Con lo que ya hay se puede implementar una version completa y coherente que cubra:

- ciudad real
- dos areas
- series temporales
- geografia
- dashboard

Solo haria falta descargar mas datos si quisierais ampliar el alcance, por ejemplo:

- datos de trafico viario reales para hacer un cruce mas fuerte entre contaminacion y flujo de vehiculos
- mas estaciones LAQN si quisierais aumentar cobertura espacial

Para una implementacion correcta del trabajo final, el paquete actual es suficiente.
