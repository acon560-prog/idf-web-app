import json
from pathlib import Path


def main():
    server_dir = Path(__file__).resolve().parent
    master_path = server_dir / "master_stations_enriched_validated.json"

    if not master_path.exists():
        raise FileNotFoundError(
            f"Master file not found at {master_path}. Run enrich_stations_fuzzy_validated.js first."
        )

    with master_path.open('r', encoding='utf-8') as fh:
        master_data = json.load(fh)

    by_province: dict[str, list] = {}
    for station in master_data:
        province = station.get('provinceCode')
        if not province:
            continue
        by_province.setdefault(province, []).append(station)

    for province, stations in by_province.items():
        province_dir = server_dir / 'data' / province
        province_dir.mkdir(parents=True, exist_ok=True)
        out_path = province_dir / 'master_stations_enriched_validated.json'
        with out_path.open('w', encoding='utf-8') as fh:
            json.dump(stations, fh, indent=2)
        print(f"Wrote {len(stations)} stations to {out_path}")


if __name__ == '__main__':
    main()
