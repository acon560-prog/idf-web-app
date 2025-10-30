# extract_volume2_stations.py

import tabula
import pandas as pd
import json
import re
import sys

pdf_path = sys.argv[1]  # e.g. "Atlas14_Volume2.pdf"
region = sys.argv[2]    # e.g. "Ohio_River_Basin"

print("Reading tables from PDF…")
#tables = tabula.read_pdf(pdf_path, pages="all", multiple_tables=True)
tables = tabula.read_pdf(pdf_path, pages="161-166", multiple_tables=True)
stations = []
for table in tables:
    df = pd.DataFrame(table)
    cols = [c.lower() for c in df.columns]
    if not ('id' in " ".join(cols) and 'lat' in " ".join(cols) and 'lon' in " ".join(cols)):
        continue

    for _, row in df.iterrows():
        sid = str(row.get('Station ID') or row.get('Station') or row.get('id') or '').strip()
        name = str(row.get('Station Name') or row.get('Name') or row.get('station name') or '').strip()
        state = str(row.get('ST') or row.get('State') or '').strip()
        try:
            lat = float(row.get('Latitude') or row.get('Lat') or row.get('lat'))
            lon = float(row.get('Longitude') or row.get('Lon') or row.get('lon'))
        except (TypeError, ValueError):
            continue

        fname = re.sub(r'\W+', '_', f"{sid}_{name}_{state}.csv")
        stations.append({
            "region": region,
            "stationId": sid,
            "name": f"{name}, {state}",
            "lat": lat,
            "lon": lon,
            "file": fname
        })

if not stations:
    print("❌ No station tables found")
    sys.exit(1)

output = f"{region}_stations_lookup.json"
with open(output, 'w') as f:
    json.dump(stations, f, indent=2)
print(f"✅ Extracted {len(stations)} stations to {output}")
