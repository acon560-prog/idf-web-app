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
    m = re.search(r"Station ID:\s*([0-9A-Za-z]+)", line or "")
    return m.group(1).strip() if m else None


def parse_years(line: str):
    # Projection window: inicial year: 2015, final year: 2050
    m1 = re.search(r"inicial year:\s*([0-9]{4})", line or "", flags=re.IGNORECASE)
    m2 = re.search(r"final year:\s*([0-9]{4})", line or "", flags=re.IGNORECASE)
    iy = int(m1.group(1)) if m1 else None
    fy = int(m2.group(1)) if m2 else None
    return iy, fy


def parse_intensity_table(lines, start_idx):
    i = start_idx
    while i < len(lines) and "t\\T" not in (lines[i] or ""):
        i += 1
    if i >= len(lines):
        return None, start_idx

    header = (lines[i] or "").strip().split()
    rps = header[1:]
    i += 1

    table = {}
    while i < len(lines):
        line = (lines[i] or "").strip()
        if not line:
            break
        low = line.lower()
        if low.startswith("precipitation") or low.startswith("model:") or line.startswith("-"):
            break
        parts = line.split()
        if not parts:
            break
        try:
            dur = int(float(parts[0]))
        except Exception:
            break
        row = {}
        for idx, rp in enumerate(rps):
            if idx + 1 >= len(parts):
                continue
            try:
                row[str(rp)] = float(parts[idx + 1])
            except Exception:
                continue
        if row:
            table[dur] = row
        i += 1
    return table, i


def parse_idf_cc_export(path: str):
    with open(path, "r", encoding="utf-8", errors="ignore") as fp:
        lines = [ln.rstrip("\n") for ln in fp.readlines()]

    station_id = None
    initial_year = None
    final_year = None
    baseline = None

    for j in range(min(40, len(lines))):
        if station_id is None:
            station_id = parse_station_id(lines[j])
        if initial_year is None or final_year is None:
            iy, fy = parse_years(lines[j])
            initial_year = initial_year or iy
            final_year = final_year or fy

    # Baseline: first intensity table in file
    for i, line in enumerate(lines[:250]):
        if (line or "").strip().lower().startswith("intensity (mm/h)"):
            baseline, _ = parse_intensity_table(lines, i)
            break

    # Scenario tables (we only need ssp585)
    ssp585_tables = []
    i = 0
    while i < len(lines):
        line = (lines[i] or "").strip()
        if line.lower().startswith("model:"):
            experiment = None
            j = i
            while j < len(lines) and j < i + 25:
                l2 = (lines[j] or "").strip()
                if l2.lower().startswith("experiment:"):
                    experiment = l2.split(":", 1)[1].strip().lower()
                if l2.lower().startswith("intensity (mm/h)"):
                    break
                j += 1
            if experiment and experiment.endswith("ssp585") and j < len(lines) and (lines[j] or "").strip().lower().startswith("intensity (mm/h)"):
                tbl, next_i = parse_intensity_table(lines, j)
                if tbl:
                    ssp585_tables.append(tbl)
                i = next_i
                continue
        i += 1

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
    rps = set()
    for d, row in baseline.items():
        rps.update(row.keys())
    rps = sorted(rps, key=lambda x: int(x) if str(x).isdigit() else 10**9)

    future_median = {}
    for d in durations:
        med_row = {}
        for rp in rps:
            vals = []
            for t in future_tables:
                v = t.get(d, {}).get(str(rp))
                if isinstance(v, (int, float)):
                    vals.append(float(v))
            m = median(vals)
            if m is not None:
                med_row[str(rp)] = float(m)
        if med_row:
            future_median[d] = med_row

    factors = {}
    for d in durations:
        base_row = baseline.get(d) or {}
        fut_row = future_median.get(d) or {}
        out_row = {}
        for rp in rps:
            b = base_row.get(str(rp))
            f = fut_row.get(str(rp))
            if isinstance(b, (int, float)) and isinstance(f, (int, float)) and b > 0:
                out_row[str(rp)] = float(f) / float(b)
        if out_row:
            factors[str(d)] = out_row

    return factors


def iter_csv_files():
    for root in EXPORTS_ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in filenames:
                if fn.lower().endswith(".csv"):
                    yield os.path.join(dirpath, fn)


def main():
    os.makedirs(OUT_ROOT, exist_ok=True)
    count = 0
    written = 0
    for path in iter_csv_files():
        count += 1
        try:
            doc = parse_idf_cc_export(path)
            sid = doc.get("stationId")
            if not sid:
                continue
            factors = build_factors(doc)
            if not factors:
                # No ssp585 tables found in this export
                continue
            out = {
                "stationId": str(sid),
                "scenario": "ssp585",
                "initialYear": doc.get("initialYear"),
                "finalYear": doc.get("finalYear"),
                "sourceFile": os.path.relpath(path, SERVER_DIR).replace("\\", "/"),
                "factors": factors,
            }
            iy = out.get("initialYear") or "unknown"
            fy = out.get("finalYear") or "unknown"
            out_path = os.path.join(OUT_ROOT, f"{sid}_{iy}-{fy}_ssp585.json")
            with open(out_path, "w", encoding="utf-8") as fp:
                json.dump(out, fp, indent=2, sort_keys=True)
            written += 1
        except Exception:
            continue

    print(f"Scanned {count} CSV files. Wrote {written} factor JSON files to {OUT_ROOT}.")


if __name__ == "__main__":
    main()

