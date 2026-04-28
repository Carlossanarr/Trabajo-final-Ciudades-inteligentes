#!/usr/bin/env python3
"""
Descarga y organiza un conjunto mínimo, reproducible y oficial de datos de Londres
para el trabajo final de Ciudades Inteligentes.

Fuentes:
- London Air Quality Network (LAQN)
- Transport for London (TfL) open data
"""

from __future__ import annotations

import csv
import re
import sys
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data_london"
RAW_DIR = DATA_DIR / "raw"
LAQN_DIR = RAW_DIR / "laqn"
TFL_DIR = RAW_DIR / "tfl"
META_DIR = DATA_DIR / "metadata"


LAQN_SITES: List[Dict[str, str]] = [
    {
        "code": "MY1",
        "name": "Westminster - Marylebone Road",
        "site_type": "Roadside",
    },
    {
        "code": "KC1",
        "name": "Kensington and Chelsea - North Kensington",
        "site_type": "Urban Background",
    },
    {
        "code": "WM6",
        "name": "Westminster - Oxford Street",
        "site_type": "Roadside",
    },
]

LAQN_SERIES = [
    ("no2_pm25_o3_2019_2024.csv", {
        "species1": "NO2m",
        "species2": "PM25m",
        "species3": "O3m",
        "start": "1-jan-2019",
        "end": "1-jan-2024",
        "period": "hourly",
        "res": "6",
        "units": "ugm3",
    }),
]

ULEZ_BOUNDARY_URL = (
    "https://s3.eu-west-1.amazonaws.com/roads.data.tfl.gov.uk/"
    "Boundaries/ULEZ_Boundary_20230829_Shape+Files.zip"
)
STATIONS_KML_URL = "https://tfl.gov.uk/cdn/static/cms/documents/stations.kml"
TFL_GTFS_URL = "https://api.tfl.gov.uk/stationdata/tfl-stationdata-gtfs.zip"


def ensure_dirs() -> None:
    for path in [DATA_DIR, RAW_DIR, LAQN_DIR, TFL_DIR, META_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def fetch_bytes(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=60) as response:
        return response.read()


def strip_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return " ".join(text.split()).strip()


def download_file(url: str, dest: Path) -> None:
    print(f"Descargando {url}")
    data = fetch_bytes(url)
    dest.write_bytes(data)
    print(f"  Guardado en {dest.relative_to(ROOT)} ({len(data) / 1024:.1f} KB)")


def build_laqn_csv_url(site_code: str, params: Dict[str, str]) -> str:
    query = {
        "site": site_code,
        "species1": params.get("species1", ""),
        "species2": params.get("species2", ""),
        "species3": params.get("species3", ""),
        "species4": params.get("species4", ""),
        "species5": params.get("species5", ""),
        "species6": params.get("species6", ""),
        "start": params["start"],
        "end": params["end"],
        "res": params["res"],
        "period": params["period"],
        "units": params["units"],
    }
    return (
        "https://www.londonair.org.uk/london/asp/downloadsite.asp?"
        + urlencode(query)
    )


def download_laqn_series() -> List[Dict[str, str]]:
    manifest_rows: List[Dict[str, str]] = []
    for site in LAQN_SITES:
        site_dir = LAQN_DIR / site["code"]
        site_dir.mkdir(parents=True, exist_ok=True)

        for filename, params in LAQN_SERIES:
            url = build_laqn_csv_url(site["code"], params)
            dest = site_dir / filename
            download_file(url, dest)
            manifest_rows.append(
                {
                    "site_code": site["code"],
                    "site_name": site["name"],
                    "site_type": site["site_type"],
                    "file": str(dest.relative_to(ROOT)),
                    "source_url": url,
                }
            )
    return manifest_rows


def parse_laqn_site_metadata(site_code: str) -> Dict[str, str]:
    url = (
        "https://www.londonair.org.uk/london/asp/publicdetails.asp"
        f"?MapType=Google&details=location&site={site_code}"
    )
    html = fetch_bytes(url).decode("utf-8", errors="replace")

    def extract(pattern: str) -> str:
        match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ""

    def extract_table_value(label: str) -> str:
        pattern = (
            rf"<td><strong>{re.escape(label)}</strong></td>\s*"
            rf"<td><em>(.*?)</em></td>"
        )
        return extract(pattern)

    lat_lon = extract_table_value("Latitude & Longitude")
    lat, lon = "", ""
    if lat_lon and "," in lat_lon:
        parts = [part.strip() for part in lat_lon.split(",", maxsplit=1)]
        if len(parts) == 2:
            lat, lon = parts

    return {
        "site_code": site_code,
        "site_name": strip_tags(
            extract(r"Your selected monitoring site\s*&raquo;\s*(.*?)\s*</")
        ),
        "operator": strip_tags(extract(r"Site operated by\s*&raquo;\s*(.*?)\s*</")),
        "address": strip_tags(extract_table_value("Address:")),
        "grid_ref": strip_tags(extract_table_value("Grid Ref:")),
        "latitude": lat,
        "longitude": lon,
        "source_url": url,
    }


def write_site_metadata_csv(rows: Iterable[Dict[str, str]], dest: Path) -> None:
    rows = list(rows)
    with dest.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Metadatos LAQN guardados en {dest.relative_to(ROOT)}")


def download_tfl_assets() -> None:
    download_file(ULEZ_BOUNDARY_URL, TFL_DIR / "ulez_boundary_shape_files.zip")
    download_file(STATIONS_KML_URL, TFL_DIR / "stations.kml")
    download_file(TFL_GTFS_URL, TFL_DIR / "tfl_stationdata_gtfs.zip")


def unzip_file(zip_path: Path, dest_dir: Path) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)
    print(f"Extraido {zip_path.relative_to(ROOT)} en {dest_dir.relative_to(ROOT)}")


def write_manifest(rows: Iterable[Dict[str, str]], dest: Path) -> None:
    rows = list(rows)
    if not rows:
        return
    with dest.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Manifest guardado en {dest.relative_to(ROOT)}")


def export_tfl_stops_csv() -> None:
    zip_path = TFL_DIR / "tfl_stationdata_gtfs.zip"
    out_path = META_DIR / "tfl_stops.csv"
    geo_out_path = META_DIR / "tfl_geo_stops.csv"
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open("stops.txt") as f:
            rows = list(csv.DictReader(f.read().decode("utf-8", errors="replace").splitlines()))

    keep_cols = ["stop_id", "stop_name", "stop_lat", "stop_lon", "location_type", "parent_station"]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keep_cols)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in keep_cols})
    print(f"CSV de paradas TfL guardado en {out_path.relative_to(ROOT)}")

    with geo_out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keep_cols)
        writer.writeheader()
        for row in rows:
            if row.get("stop_lat") and row.get("stop_lon"):
                writer.writerow({col: row.get(col, "") for col in keep_cols})
    print(f"CSV geoespacial de TfL guardado en {geo_out_path.relative_to(ROOT)}")


def main() -> int:
    ensure_dirs()

    manifest_rows: List[Dict[str, str]] = []

    try:
        manifest_rows.extend(download_laqn_series())
        site_metadata = [parse_laqn_site_metadata(site["code"]) for site in LAQN_SITES]
        write_site_metadata_csv(site_metadata, META_DIR / "laqn_sites.csv")

        download_tfl_assets()
        unzip_file(TFL_DIR / "ulez_boundary_shape_files.zip", TFL_DIR / "ulez_boundary")
        unzip_file(TFL_DIR / "tfl_stationdata_gtfs.zip", TFL_DIR / "tfl_stationdata_gtfs")
        export_tfl_stops_csv()

        write_manifest(manifest_rows, META_DIR / "laqn_download_manifest.csv")
    except (HTTPError, URLError, TimeoutError) as exc:
        print(f"Fallo durante la descarga: {exc}", file=sys.stderr)
        return 1

    print("\nDescarga de Londres completada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
