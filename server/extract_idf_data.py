import os
import json
import re

# Directory with all ECCC txt files
DATA_DIR = './data'
OUTPUT_FILE = 'idf_data_by_station.json'

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


def main():
    out = {}
    for fname in os.listdir(DATA_DIR):
        if not fname.endswith('.txt'):
            continue
        station_id = extract_station_id_from_filename(fname)
        with open(os.path.join(DATA_DIR, fname), encoding='latin-1') as f:
            lines = f.readlines()
        idf_table = parse_table_2a(lines)
        print("Station ID:", station_id, type(station_id))
        out[station_id] = idf_table

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as out_f:
        json.dump(out, out_f, indent=2)

if __name__ == '__main__':
    main()
