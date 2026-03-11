# IDF_CC factor files (compact)

This folder stores **compact climate-change multipliers** derived from IDF_CC exports.

## File format

Each JSON file contains:

- `stationId`: ECCC station ID used by the IDF dataset
- `scenario`: currently `ssp585` (high emissions)
- `initialYear` / `finalYear`: projection window from the export (e.g. `2015`–`2050`)
- `factors`: a nested map of **duration minutes** -> **return period years** -> **multiplier**

Example usage in code:

- `adjusted_intensity = historical_intensity * factor`

## Generating factor files

1) Put one or more IDF_CC export `.csv` files into either:

- `server/data/idf_cc_exports/`
- `server/data/idf_cc/`

2) Run the generator:

```bash
python3 server/scripts/generate_idf_cc_factors.py
```

It scans the export files and writes factor JSONs into this folder.

## Runtime behavior

When the API is called with:

- `/api/idf/curves?stationId=...&climate=cc_2050_high`

the server will:

1) Prefer a matching factor JSON in this folder (fast).
2) Fall back to parsing an export CSV if a factor file is not present (slower).

