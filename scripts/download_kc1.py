#!/usr/bin/env python3
import urllib.request
import os

url = "https://www.londonair.org.uk/london/asp/downloadsite.asp?site=KC1&species1=O3&species2=&species3=&species4=&species5=&species6=&start=1-jan-2009&end=1-jan-2021&res=6&period=hourly&units=ugm3"
os.makedirs("data_london/raw/laqn/KC1", exist_ok=True)
out_file = "data_london/raw/laqn/KC1/o3_hourly_KC1_2009_2021.csv"

print(f"Descargando {url} ...")
urllib.request.urlretrieve(url, out_file)
print(f"Descarga completada en {out_file}")
