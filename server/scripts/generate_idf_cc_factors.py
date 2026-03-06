import json
import os
import re
import statistics
from collections import deque


HERE = os.path.dirname(__file__)
SERVER_DIR = os.path.abspath(os.path.join(HERE, ".."))
EXPORTS_ROOTS = [
    os.path.join(SERVER_DIR, "data", "idf_cc_exports"),
    os.path.join(SERVER_DIR, "data", "idf_cc"),
]
OUT_ROOT = os.path.join(SERVER_DIR, "data", "idf_cc_factors")
JSON_RESPONSE_SUFFIX = "fncloaddatappt.response.json"


RETURN_PERIOD_KEYS = ("2", "5", "10", "25", "50", "100")
DURATION_KEY_CANDIDATES = (
    "duration",
    "durationmin",
    "durationminutes",
    "durationminute",
    "t",
    "time",
    "d",
)
RETURN_PERIOD_PATTERNS = [
    re.compile(r"^(?:rp|tr|t)?\s*([0-9]{1,3})$"),
    re.compile(r"^([0-9]{1,3})\s*(?:yr|year|ans?)$"),
    re.compile(r"^(?:returnperiod)?\s*([0-9]{1,3})$"),
]


def _coerce_float(value):
    if value in (None, "", "null", "None"):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "")
    try:
        return float(text)
    except Exception:
        return None


def _coerce_int(value):
    number = _coerce_float(value)
    if number is None:
        return None
    try:
        return int(round(number))
    except Exception:
        return None


def _normalize_key(key):
    return re.sub(r"[^a-z0-9]", "", str(key or "").lower())


def _parse_duration_from_key(key):
    text = str(key or "").strip().lower().replace(" ", "")
    if not text:
        return None

    # Common "t5min" / "t1h" / "t24h" / "duration_60" variants.
    match_min = re.match(r"^t?([0-9]+(?:\.[0-9]+)?)m(?:in)?$", text)
    if match_min:
        return int(round(float(match_min.group(1))))

    match_hr = re.match(r"^t?([0-9]+(?:\.[0-9]+)?)h$", text)
    if match_hr:
        return int(round(float(match_hr.group(1)) * 60))

    match_day = re.match(r"^t?([0-9]+(?:\.[0-9]+)?)d$", text)
    if match_day:
        return int(round(float(match_day.group(1)) * 24 * 60))

    match_plain = re.match(r"^(?:duration)?_?([0-9]{1,5})$", text)
    if match_plain:
        value = int(match_plain.group(1))
        if value > 0:
            return value
    return None


def _parse_return_period(key):
    normalized = _normalize_key(key)
    if normalized in RETURN_PERIOD_KEYS:
        return normalized
    for pattern in RETURN_PERIOD_PATTERNS:
        match = pattern.match(normalized)
        if match and match.group(1) in RETURN_PERIOD_KEYS:
            return match.group(1)
    return None


def _extract_jsonish(text):
    if not isinstance(text, str):
        return None
    stripped = text.strip()
    if not stripped:
        return None
    if not ((stripped.startswith("{") and stripped.endswith("}")) or (stripped.startswith("[") and stripped.endswith("]"))):
        return None
    try:
        return json.loads(stripped)
    except Exception:
        return None


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


def parse_idf_cc_export_text(path: str):
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


def _collect_json_nodes(payload):
    queue = deque([payload])
    seen = set()

    while queue:
        node = queue.popleft()
        node_id = id(node)
        if node_id in seen:
            continue
        seen.add(node_id)
        yield node

        if isinstance(node, dict):
            for value in node.values():
                queue.append(value)
        elif isinstance(node, list):
            for item in node:
                queue.append(item)
        elif isinstance(node, str):
            parsed = _extract_jsonish(node)
            if parsed is not None:
                queue.append(parsed)


def _table_from_duration_columns(rows):
    if not isinstance(rows, list) or not rows:
        return None
    if not all(isinstance(row, dict) for row in rows):
        return None

    duration_keys = set()
    for row in rows:
        for key in row.keys():
            duration = _parse_duration_from_key(key)
            if duration:
                duration_keys.add((key, duration))

    if not duration_keys:
        return None

    # This representation (year + duration columns) is not an IDF return-period table.
    # We skip it deliberately to avoid manufacturing incorrect factors.
    return None


def _table_from_duration_rows(rows):
    if not isinstance(rows, list) or not rows:
        return None
    if not all(isinstance(row, dict) for row in rows):
        return None

    table = {}

    for row in rows:
        duration = None
        normalized_map = { _normalize_key(k): k for k in row.keys() }
        for candidate in DURATION_KEY_CANDIDATES:
            key = normalized_map.get(candidate)
            if key is not None:
                duration = _coerce_int(row.get(key))
                break
        if duration is None:
            # Try a key that itself encodes duration.
            for key in row.keys():
                duration_from_key = _parse_duration_from_key(key)
                if duration_from_key:
                    duration = duration_from_key
                    break

        if duration is None or duration <= 0:
            continue

        out_row = {}
        for key, value in row.items():
            rp = _parse_return_period(key)
            if rp is None:
                continue
            numeric = _coerce_float(value)
            if numeric is None:
                continue
            out_row[rp] = float(numeric)

        if out_row:
            table[int(duration)] = out_row

    # A useful IDF table should have several durations and return periods.
    if len(table) < 3:
        return None
    union_rps = set()
    for rp_row in table.values():
        union_rps.update(rp_row.keys())
    if len(union_rps) < 2:
        return None
    return table


def _table_from_text_blob(text):
    if not isinstance(text, str):
        return None
    if "intensity" not in text.lower():
        return None
    lines = [line.rstrip("\n") for line in text.splitlines()]
    for idx, line in enumerate(lines[:300]):
        if (line or "").strip().lower().startswith("intensity (mm/h)"):
            table, _ = parse_intensity_table(lines, idx)
            if table:
                return table
    return None


def parse_idf_cc_export_json(path: str):
    with open(path, "r", encoding="utf-8", errors="ignore") as fp:
        raw_text = fp.read()

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        return {
            "stationId": None,
            "initialYear": None,
            "finalYear": None,
            "baseline": None,
            "ssp585Tables": [],
        }

    station_id = None
    initial_year = None
    final_year = None

    baseline_candidates = []
    ssp585_candidates = []

    for node in _collect_json_nodes(payload):
        if station_id is None and isinstance(node, dict):
            sid = node.get("StationId") or node.get("stationId")
            if sid not in (None, ""):
                station_id = str(sid).strip()

        if isinstance(node, str):
            if initial_year is None or final_year is None:
                parsed_initial, parsed_final = parse_years(node)
                initial_year = initial_year or parsed_initial
                final_year = final_year or parsed_final

            maybe_table = _table_from_text_blob(node)
            if maybe_table:
                low = node.lower()
                if "ssp585" in low:
                    ssp585_candidates.append(maybe_table)
                else:
                    baseline_candidates.append(maybe_table)
            continue

        if isinstance(node, list):
            # Try row-based IDF table forms.
            table = _table_from_duration_rows(node)
            if table:
                node_text = json.dumps(node[:3], ensure_ascii=False).lower()
                if "ssp585" in node_text:
                    ssp585_candidates.append(table)
                else:
                    baseline_candidates.append(table)
                continue

            # Ignore year/duration-column tables such as annual maxima records.
            _table_from_duration_columns(node)

    baseline = None
    if baseline_candidates:
        baseline = max(
            baseline_candidates,
            key=lambda table: sum(len(row) for row in table.values()),
        )

    ssp585_tables = []
    if ssp585_candidates:
        ssp585_tables = ssp585_candidates

    return {
        "stationId": station_id,
        "initialYear": initial_year,
        "finalYear": final_year,
        "baseline": baseline,
        "ssp585Tables": ssp585_tables,
    }


def parse_idf_cc_export(path: str):
    lower = str(path).lower()
    if lower.endswith(".csv"):
        return parse_idf_cc_export_text(path)
    if lower.endswith(".json"):
        return parse_idf_cc_export_json(path)
    return parse_idf_cc_export_text(path)


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


def iter_export_files():
    for root in EXPORTS_ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            for filename in filenames:
                low = filename.lower()
                if low.endswith(".csv"):
                    yield os.path.join(dirpath, filename)
                    continue
                if low.endswith(".json") and low.endswith(JSON_RESPONSE_SUFFIX):
                    yield os.path.join(dirpath, filename)


def main():
    os.makedirs(OUT_ROOT, exist_ok=True)

    scanned = 0
    written = 0
    for path in iter_export_files():
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
