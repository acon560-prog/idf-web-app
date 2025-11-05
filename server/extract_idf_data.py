import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = BASE_DIR / 'data'
DEFAULT_OUTPUT_NAME = 'idf_data_by_station.json'

def parse_table_2a(lines):
    results = []
    in_table = False
    data_started = False

    duration_pattern = re.compile(r'^\d+(\.\d+)?\s(min|h)$')

    def clean_value(val):
        return None if val == -99.9 else val
    
    for i, line in enumerate(lines):
        if 'Table 2a' in line:
            in_table = True
            continue

        if in_table:
            line_strip = line.strip()
            # Check if line starts a duration row
            parts = line_strip.split()

            # Compose a possible duration string
            if len(parts) > 1:
                duration_str = parts [0] + ' ' + parts [1]
            elif parts:
                duration_str = parts [0]
            else:
                duration_str = ''

            if not data_started:
                # Start data reading if pattern matches
                if duration_pattern.match(duration_str):
                    data_started = True
                else:
                    continue

            if data_started:
                if not duration_pattern.match(duration_str):
                    # Stop parsing when no more duration rows
                    break

                # Extract values, ignoring last column (#Years)
                if parts [1] in ['min', 'h']:
                    duration = parts [0] + ' ' + parts [1]
                    values = parts [2:-1] 
                else:
                    duration = parts [0]
                    values = parts [1:-1]

                try:
                    val_0 = clean_value(float(values [0]))
                    val_1 = clean_value(float(values [1]))
                    val_2 = clean_value(float(values [2]))
                    val_3 = clean_value(float(values [3]))
                    val_4 = clean_value(float(values [4]))
                    val_5 = clean_value(float(values [5]))
                except Exception:
                    continue

                results.append({
                    'duration': duration,
                    '2': val_0,
                    '5': val_1,
                    '10': val_2,
                    '25': val_3,
                    '50': val_4,
                    '100': val_5,
                })

    return results





def extract_station_id_from_filename(fname):
    # Example: idf_v3-30_2022_10_31_710_QC_710S005_INUKJUAK.txt
    match = re.search(r'_(\w{5,})\.txt$', fname)
    return match.group(1) if match else fname.split('.')[0]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description='Extract IDF data from Environment Canada station text files.'
    )
    parser.add_argument(
        '--data-dir', '-d', '-DataDir',
        default=str(DEFAULT_DATA_DIR),
        help='Directory containing the Environment Canada IDF text files. '
             'Default is the "data" directory that sits next to this script.'
    )
    parser.add_argument(
        '--province', '-p', '-Province',
        help='Optional province code (e.g. ON, QC). When provided and the data directory '
             'matches the default, the script will look inside a province-specific '
             'subdirectory.'
    )
    parser.add_argument(
        '--output', '-o', '-Output',
        help='Path for the generated JSON file. Defaults to <data-dir>/idf_data_by_station.json.'
    )
    return parser.parse_args(argv)


def resolve_data_dir(data_dir: Path, province: Optional[str]) -> Path:
    data_dir = data_dir.expanduser()
    if not data_dir.is_absolute():
        data_dir = (BASE_DIR / data_dir).resolve()

    if province:
        province = province.strip()
        if data_dir.name.lower() != province.lower():
            candidate = data_dir / province
            if candidate.is_dir():
                data_dir = candidate

    if not data_dir.is_dir():
        raise FileNotFoundError(f'Data directory does not exist: {data_dir}')

    return data_dir


def resolve_output_path(output: Optional[str], data_dir: Path) -> Path:
    if output:
        path = Path(output).expanduser()
        if not path.is_absolute():
            path = (BASE_DIR / path).resolve()
    else:
        path = data_dir / DEFAULT_OUTPUT_NAME

    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def main(argv=None):
    args = parse_args(argv)

    data_dir = resolve_data_dir(Path(args.data_dir), args.province)
    output_path = resolve_output_path(args.output, data_dir)

    txt_files = sorted(p for p in data_dir.iterdir() if p.suffix.lower() == '.txt')

    if not txt_files:
        raise FileNotFoundError(
            f'No .txt files found in {data_dir}. Ensure the directory contains Environment '
            'Canada IDF text files.'
        )

    out: Dict[str, List[Dict[str, Optional[float]]]] = {}

    for txt_file in txt_files:
        station_id = extract_station_id_from_filename(txt_file.name)
        with txt_file.open(encoding='latin-1') as f:
            lines = f.readlines()
        idf_table = parse_table_2a(lines)
        print('Processed station:', station_id)
        out[station_id] = idf_table

    with output_path.open('w', encoding='utf-8') as out_f:
        json.dump(out, out_f, indent=2)

    print(f'Wrote IDF data for {len(out)} stations to {output_path}')


if __name__ == '__main__':
    main()
