import argparse
import json
import os
import re
from pathlib import Path

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


def extract_station_id(path: Path) -> str:
    match = re.search(r'_(\w{5,})\.txt$', path.name)
    return match.group(1) if match else path.stem


def main():
    args = parse_args()
    base_dir = Path(args.data_dir)

    output = {}
    for txt_path in iter_txt_files(base_dir, args.province):
        with txt_path.open(encoding='latin-1') as fh:
            lines = fh.readlines()
        idf_table = parse_table_2a(lines)
        output[extract_station_id(txt_path)] = idf_table

    with open(args.output, 'w', encoding='utf-8') as out_f:
        json.dump(output, out_f, indent=2)


if __name__ == '__main__':
    main()
