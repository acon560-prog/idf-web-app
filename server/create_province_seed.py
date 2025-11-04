import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Create a provincial station seed JSON from eccc_climate_stations_full.json")
    parser.add_argument("province", help="Province code (e.g. QC, ON, BC)")
    parser.add_argument("output", nargs="?", help="Optional output path; defaults to server/<province.lower()>_seed.json")
    args = parser.parse_args()

    province = args.province.upper()

    server_dir = Path(__file__).resolve().parent
    source_path = server_dir / "eccc_climate_stations_full.json"
    if not source_path.exists():
        raise FileNotFoundError(f"Cannot find {source_path}")

    stations = json.loads(source_path.read_text(encoding="utf-8"))
    subset = [s for s in stations if s.get("provinceCode") == province]

    if not subset:
        print(f"No stations found for province {province}.")
    out_path = Path(args.output) if args.output else server_dir / f"{province.lower()}_seed.json"
    out_path.write_text(json.dumps(subset, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(subset)} stations to {out_path}")


if __name__ == "__main__":
    main()
