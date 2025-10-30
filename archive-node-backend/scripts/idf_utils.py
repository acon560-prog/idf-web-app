# server/scripts/idf_utils.py

import os
import json
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO


#########################
# Parsing and Utilities #
#########################

def parse_duration(duration_str):
    if isinstance(duration_str, list):
        # Flatten if input is list
        duration_str = ' '.join(map(str, duration_str))
    parts = duration_str.split()
    if len(parts) != 2:
        raise ValueError(f"Invalid duration format: {duration_str}")

    value = float(parts[0])  # Use first element as numeric value
    unit = parts[1]          # Use second element as unit string

    if unit == 'min':
        duration_minutes = value
        duration_hours = value / 60.0
    elif unit == 'h' or unit == 'hr' or unit == 'hour' or unit == 'hours':
        duration_minutes = value * 60.0
        duration_hours = value
    else:
        raise ValueError(f"Unknown duration unit: {unit}")

    return duration_minutes, duration_hours


def mm_to_inch(mm):
    return mm / 25.4

def inch_to_mm(inch):
    return inch * 25.4

def compute_intensity(depth, duration_minutes, duration_hours, to_inches=False):
    """Compute intensity based on duration, auto-handle missing data."""
    if depth is None:
        return None
    if duration_minutes <= 60:
        intensity = depth * (60 / duration_minutes)
    else:
        intensity = depth / duration_hours
    if to_inches:
        intensity = mm_to_inch(intensity)
    return intensity

import json
import os

idf_data_cache = None

def load_idf_data(station_id, data_dir):
    global idf_data_cache
    if idf_data_cache is None:
        # Use absolute path based on the location of this file (idf_utils.py)
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(BASE_DIR, '..', 'data', 'idf_data_by_station.json')
        json_path = os.path.abspath(json_path)
        with open(json_path, 'r') as f:
            idf_data_cache = json.load(f)

    if station_id in idf_data_cache:
        return idf_data_cache[station_id]

    raise FileNotFoundError(f"No IDF data found for station: {station_id}")



#########################
# Plotting              #
#########################

def plot_idf_curves(rainfall_data, station_id, units='mm/hr', return_periods=None, save_path=None):
    """
    Plot IDF curves (precipitation intensity vs. duration) for a given station.
    - rainfall_data: dictionary from your JSON, keyed by station IDs.
    - station_id: string, station key.
    - units: 'mm/hr' (default) or 'in/hr'
    - return_periods: list, defaults to ['2', '5', '10', '25', '50', '100']
    - save_path: if given, plot is saved as .png (recommended for web apps)
    """
    if station_id not in rainfall_data:
        raise KeyError(f"Station ID '{station_id}' not found in data")

    data = rainfall_data[station_id]
    default_rps = ['2', '5', '10', '25', '50', '100']
    rps = return_periods if return_periods is not None else default_rps

    durations_hr = []
    intensities = {rp: [] for rp in rps}

    for entry in data:
        dmin, dhr = parse_duration(entry['duration'])
        durations_hr.append(dhr)
        for rp in rps:
            val = entry.get(rp)
            inten = compute_intensity(val, dmin, dhr, to_inches=(units == 'in/hr'))
            intensities[rp].append(inten)

    plt.figure(figsize=(10, 6))

    for rp in rps:
        x_vals = []
        y_vals = []
        for x, y in zip(durations_hr, intensities[rp]):
            if y is not None:
                x_vals.append(x)
                y_vals.append(y)
        plt.plot(x_vals, y_vals, marker='o', label=f'{rp}-year')

    plt.xscale('log')
    plt.xlabel('Duration (hours)')
    plt.ylabel(f'Rainfall Intensity ({units})')
    plt.title(f'IDF Curves for Station: {station_id}')
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.legend()
    plt.tight_layout()
    if save_path:
    # Check if save_path is a string or a file-like buffer
        if isinstance(save_path, str):
            plt.savefig(save_path, format='png')
        else:
            # Assume file-like object (BytesIO)
            plt.savefig(save_path, format='png')
            save_path.seek(0)  # Rewind buffer to start
        plt.close()
    else:
        plt.show()


#########################
# Example Loader/Caller #
#########################

def get_idf_plot_for_station(
    station_id, data_dir, rainfall_data=None, units='mm/hr', save_path=None
):
    """
    Loads the IDF data for a station, creates the plot, and saves or returns as needed.
    - station_id: key as used in your JSON files (e.g., "2022_10_31_614_ON_6144478_LONDON_CS")
    - data_dir: path to directory with parsed JSON files
    - rainfall_data: if already loaded, pass as dict
    - units: 'mm/hr' or 'in/hr'
    - save_path: where to save image (optional, for web app serving)
    """
    # If rainfall_data not passed, load from file
    if rainfall_data is None:
        rainfall_data = load_idf_data(station_id, data_dir)
        rainfall_data = {station_id: rainfall_data}  # wrap for plot function format
    plot_idf_curves(rainfall_data, station_id, units=units, save_path=save_path)

# End of idf_utils.py
