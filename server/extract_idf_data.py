import argparse
import json
import os
import re
from pathlib import Path
from difflib import SequenceMatcher

DURATION_PATTERN = re.compile(r'^\d+(\.\d+)?\s(min|h)$')


def parse_args():
    parser = argparse.ArgumentParser(description='Parse ECCC IDF text files into JSON.')
    parser.add_argument(
        '--data-dir',
        default='server/data',
        help='Root directory containing province folders (default: server/data).'
    )
    parser.add_argument(
        '--province',
        help='Optional province code (e.g. QC, ON, SK). If omitted, all subdirectories are scanned.'
    )
    parser.add_argument(
        '--output',
        default='idf_data_by_station.json',
        help='Output JSON path (default: idf_data_by_station.json).'
    )
    return parser.parse_args()


def iter_txt_files(base_dir: Path, province: str | None):
    base = base_dir.resolve()

    if province:
        province_dir = base / province
        if not province_dir.is_dir():
            raise FileNotFoundError(f'Province directory not found: {province_dir}')
        folders = [province_dir]
    else:
        folders = [p for p in base.iterdir() if p.is_dir()] or [base]

    for folder in folders:
        for path in folder.rglob('*.txt'):
            yield path


def parse_table_2a(lines):
    results = []
    in_table = False
    data_started = False

    def clean_value(val):
        return None if val == -99.9 else val

    for line in lines:
        if 'Table 2a' in line:
            in_table = True
            continue

        if not in_table:
            continue

        parts = line.strip().split()
        if not parts:
            continue

        if len(parts) > 1:
            duration_candidate = parts[0] + ' ' + parts[1]
        else:
            duration_candidate = parts[0]

        if not data_started:
            if DURATION_PATTERN.match(duration_candidate):
                data_started = True
            else:
                continue

        if not DURATION_PATTERN.match(duration_candidate):
            break

        if len(parts) > 1 and parts[1] in {'min', 'h'}:
            duration = parts[0] + ' ' + parts[1]
            values = parts[2:-1]
        else:
            duration = parts[0]
            values = parts[1:-1]

        if len(values) < 6:
            continue

        try:
            results.append({
                'duration': duration,
                '2': clean_value(float(values[0])),
                '5': clean_value(float(values[1])),
                '10': clean_value(float(values[2])),
                '25': clean_value(float(values[3])),
                '50': clean_value(float(values[4])),
                '100': clean_value(float(values[5])),
            })
        except ValueError:
            continue

    return results


STATION_ID_PATTERN = re.compile(r'_(\d{7}|\d{3}[A-Z]{2}\d)_', re.IGNORECASE)


def extract_station_id(path: Path) -> str | None:
    match = STATION_ID_PATTERN.search(path.name)
    return match.group(1) if match else None


def extract_station_name(path: Path) -> str:
    # Remove prefix like idf_v3-30_2022_10_31_101_BC_
    name_part = path.name
    prefix = re.compile(r'^idf_v3-30_\d{4}_\d{2}_\d{2}_\d+_[A-Z]{2}_')
    name_part = prefix.sub('', name_part)
    # Remove extension and suffix variants (_qq, _r, _t)
    name_part = name_part.rsplit('.', 1)[0]
    name_part = re.sub(r'_(qq|r|t)$', '', name_part)
    return name_part.upper()


def normalize(s: str) -> str:
    return re.sub(r'[^A-Z0-9]', '', s.upper())


def main():
    args = parse_args()
    base_dir = Path(args.data_dir)

    # Load master metadata for fallback matching
    province = args.province.upper() if args.province else None
    master_path = base_dir.parent / 'data' / (province or '') / 'master_stations_enriched_validated.json'
    master_lookup = {}
    if master_path.exists():
        with master_path.open(encoding='utf-8') as fh:
            for record in json.load(fh):
                sid = record.get('stationId')
                if sid:
                    master_lookup[sid] = record

    output = {}
    name_index = {}

    for txt_path in iter_txt_files(base_dir, province):
        station_id = extract_station_id(txt_path)
        with txt_path.open(encoding='latin-1') as fh:
            lines = fh.readlines()
        idf_table = parse_table_2a(lines)

        if station_id:
            output[station_id] = idf_table
            continue

        # Fallback: attempt to match by station name
        raw_name = extract_station_name(txt_path)
        normalized = normalize(raw_name)

        # Build name index from master lookup on first use
        if not name_index and master_lookup:
            for sid, record in master_lookup.items():
                name = record.get('name') or record.get('lookupName') or ''
                name_index[sid] = normalize(name)

        best_sid = None
        best_score = 0.0
        for sid, nname in name_index.items():
            score = SequenceMatcher(None, normalized, nname).ratio()
            if score > best_score:
                best_score = score
                best_sid = sid

        if best_sid and best_score >= 0.85:  # accept close matches
            output[best_sid] = idf_table
        else:
            # fallback: store under raw name to avoid data loss
            output[raw_name] = idf_table

    with open(args.output, 'w', encoding='utf-8') as out_f:
        json.dump(output, out_f, indent=2)


if __name__ == '__main__':
    main()
