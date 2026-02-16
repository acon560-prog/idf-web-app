import json
import os
import re
import statistics


HERE = os.path.dirname(__file__)
SERVER_DIR = os.path.abspath(os.path.join(HERE, ".."))
EXPORTS_ROOTS = [
    os.path.join(SERVER_DIR, "data", "idf_cc_exports"),
    os.path.join(SERVER_DIR, "data", "idf_cc"),
]
OUT_ROOT = os.path.join(SERVER_DIR, "data", "idf_cc_factors")


def median(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    try:
        return float(statistics.median(values))
    except Exception:
        values = sorted(values)
        mid = len(values) // 2
        if len(values) % 2 == 1:
            return float(values[mid])
        return float(values[mid - 1] + values[mid]) / 2.0


def parse_station_id(line: str):
    match = re.search(r"Station ID:\s*([0-9A-Za-z]+)", line or "")
    return match.group(1).strip() if match else None


def parse_years(line: str):
    # Projection window: inicial year: 2015, final year: 2050
    match_initial = re.search(r"inicial year:\s*([0-9]{4})", line or "", flags=re.IGNORECASE)
    match_final = re.search(r"final year:\s*([0-9]{4})", line or "", flags=re.IGNORECASE)
    initial_year = int(match_initial.group(1)) if match_initial else None
    final_year = int(match_final.group(1)) if match_final else None
    return initial_year, final_year


def parse_intensity_table(lines, start_idx):
    idx = start_idx
    while idx < len(lines) and "t\\T" not in (lines[idx] or ""):
        idx += 1
    if idx >= len(lines):
        return None, start_idx

    header = (lines[idx] or "").strip().split()
    return_periods = header[1:]
    idx += 1

    table = {}
    while idx < len(lines):
        line = (lines[idx] or "").strip()
        if not line:
            break
        low = line.lower()
        if low.startswith("precipitation") or low.startswith("model:") or line.startswith("-"):
            break
        parts = line.split()
        if not parts:
            break
        try:
            duration = int(float(parts[0]))
        except Exception:
            break

        row = {}
        for rp_idx, rp in enumerate(return_periods):
            if rp_idx + 1 >= len(parts):
                continue
            try:
                row[str(rp)] = float(parts[rp_idx + 1])
            except Exception:
                continue
        if row:
            table[duration] = row
        idx += 1
    return table, idx


def parse_idf_cc_export(path: str):
    with open(path, "r", encoding="utf-8", errors="ignore") as fp:
        lines = [line.rstrip("\n") for line in fp.readlines()]

    station_id = None
    initial_year = None
    final_year = None
    baseline = None

    for idx in range(min(40, len(lines))):
        if station_id is None:
            station_id = parse_station_id(lines[idx])
        if initial_year is None or final_year is None:
            parsed_initial, parsed_final = parse_years(lines[idx])
            initial_year = initial_year or parsed_initial
            final_year = final_year or parsed_final

    # Baseline: first intensity table in file.
    for idx, line in enumerate(lines[:250]):
        if (line or "").strip().lower().startswith("intensity (mm/h)"):
            baseline, _ = parse_intensity_table(lines, idx)
            break

    # Scenario tables: we only need SSP5-8.5.
    ssp585_tables = []
    idx = 0
    while idx < len(lines):
        line = (lines[idx] or "").strip()
        if line.lower().startswith("model:"):
            experiment = None
            lookahead = idx
            while lookahead < len(lines) and lookahead < idx + 25:
                look_line = (lines[lookahead] or "").strip()
                if look_line.lower().startswith("experiment:"):
                    experiment = look_line.split(":", 1)[1].strip().lower()
                if look_line.lower().startswith("intensity (mm/h)"):
                    break
                lookahead += 1

            if (
                experiment
                and experiment.endswith("ssp585")
                and lookahead < len(lines)
                and (lines[lookahead] or "").strip().lower().startswith("intensity (mm/h)")
            ):
                table, next_idx = parse_intensity_table(lines, lookahead)
                if table:
                    ssp585_tables.append(table)
                idx = next_idx
                continue
        idx += 1

    return {
        "stationId": station_id,
        "initialYear": initial_year,
        "finalYear": final_year,
        "baseline": baseline,
        "ssp585Tables": ssp585_tables,
    }


def build_factors(doc):
    baseline = doc.get("baseline") or {}
    future_tables = doc.get("ssp585Tables") or []
    if not baseline or not future_tables:
        return None

    durations = sorted(baseline.keys())
    return_periods = set()
    for _duration, row in baseline.items():
        return_periods.update(row.keys())
    return_periods = sorted(return_periods, key=lambda value: int(value) if str(value).isdigit() else 10**9)

    future_median = {}
    for duration in durations:
        median_row = {}
        for rp in return_periods:
            values = []
            for table in future_tables:
                value = table.get(duration, {}).get(str(rp))
                if isinstance(value, (int, float)):
                    values.append(float(value))
            med = median(values)
            if med is not None:
                median_row[str(rp)] = float(med)
        if median_row:
            future_median[duration] = median_row

    factors = {}
    for duration in durations:
        base_row = baseline.get(duration) or {}
        fut_row = future_median.get(duration) or {}
        out_row = {}
        for rp in return_periods:
            base_value = base_row.get(str(rp))
            fut_value = fut_row.get(str(rp))
            if isinstance(base_value, (int, float)) and isinstance(fut_value, (int, float)) and base_value > 0:
                out_row[str(rp)] = float(fut_value) / float(base_value)
        if out_row:
            factors[str(duration)] = out_row

    return factors


def iter_csv_files():
    for root in EXPORTS_ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            for filename in filenames:
                if filename.lower().endswith(".csv"):
                    yield os.path.join(dirpath, filename)


def main():
    os.makedirs(OUT_ROOT, exist_ok=True)

    scanned = 0
    written = 0
    for path in iter_csv_files():
        scanned += 1
        try:
            doc = parse_idf_cc_export(path)
            station_id = doc.get("stationId")
            if not station_id:
                continue

            factors = build_factors(doc)
            if not factors:
                # No SSP5-8.5 table was found for this export.
                continue

            output = {
                "stationId": str(station_id),
                "scenario": "ssp585",
                "initialYear": doc.get("initialYear"),
                "finalYear": doc.get("finalYear"),
                "sourceFile": os.path.relpath(path, SERVER_DIR).replace("\\", "/"),
                "factors": factors,
            }
            initial_year = output.get("initialYear") or "unknown"
            final_year = output.get("finalYear") or "unknown"
            out_path = os.path.join(OUT_ROOT, f"{station_id}_{initial_year}-{final_year}_ssp585.json")

            with open(out_path, "w", encoding="utf-8") as fp:
                json.dump(output, fp, indent=2, sort_keys=True)
            written += 1
        except Exception:
            continue

    print(f"Scanned {scanned} CSV files. Wrote {written} factor JSON files to {OUT_ROOT}.")


if __name__ == "__main__":
    main()
