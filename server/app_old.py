# File: civil-eng-website/server/app.py

from flask import Flask, request, jsonify, send_from_directory
import sys
import os
import io
from collections import OrderedDict
import math
import json
import re

# **CRITICAL FIX:** Add the 'archive-node-backend' directory to the Python path.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'archive-node-backend')))

from scripts.idf_utils import load_idf_data, parse_duration, compute_intensity, get_idf_plot_for_station

# Define the path to the stations metadata file. It's in server/data.
STATIONS_DATA_PATH = os.path.join(
    os.path.dirname(__file__),
    'data',
    'master_stations_enriched_validated.json'
)

# Define the path to the single IDF data JSON file. It's in archive-node-backend.
IDF_DATA_PATH = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'archive-node-backend')),
    'idf_data_by_station.json'
)

# Load the stations metadata once at startup
STATIONS_DATA = []
try:
    with open(STATIONS_DATA_PATH, 'r', encoding='utf-8') as f:
        STATIONS_DATA = json.load(f)
    print(f"Successfully loaded {len(STATIONS_DATA)} stations metadata.")
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"Error loading stations data: {e}")

# Load the IDF data once at startup
IDF_DATA = {}
IDF_KEY_MAPPING = {} 
try:
    with open(IDF_DATA_PATH, 'r', encoding='utf-8') as f:
        IDF_DATA = json.load(f)
    # Populate the mapping dictionary by extracting the stationId from the keys
    for key in IDF_DATA:
        # **NEW REGEX:** Match a 5- to 7-digit number following a province code
        match = re.search(r'_[A-Z]{2}_(\d{5,7})_', key)
        if match:
            station_id = match.group(1)
            IDF_KEY_MAPPING[station_id] = key
        else:
            # Fallback for simple station IDs that are keys themselves
            IDF_KEY_MAPPING[key] = key

    print(f"Successfully loaded IDF data for {len(IDF_DATA)} stations.")
    print(f"Successfully created IDF key mapping for {len(IDF_KEY_MAPPING)} stations.")

except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"Error loading IDF data: {e}")

app = Flask(__name__)
app.json.sort_keys = False

# The Haversine formula translated to Python
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Radius of Earth in kilometers
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance

# Helper function to convert duration strings to minutes
def duration_to_minutes(duration_str):
    """Converts a duration string (e.g., '10 min', '1 hr') to an integer in minutes."""
    try:
        parts = duration_str.split()
        if len(parts) != 2:
            return None
        
        value = int(parts[0])
        unit = parts[1].lower()
        
        if unit.startswith('min'):
            return value
        elif unit.startswith('hr'):
            return value * 60
        else:
            return None
    except (ValueError, IndexError):
        return None

@app.route('/api/stations')
def stations():
    """Return all available weather stations from the loaded data"""
    return jsonify(STATIONS_DATA)

@app.route('/api/nearest-station')
def nearest_station():
    """Finds the nearest weather station to a given latitude and longitude."""
    try:
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
        print(f"Received request for nearest station at Lat: {lat}, Lon: {lon}")
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid latitude or longitude"}), 400

    if not STATIONS_DATA:
        return jsonify({"error": "Stations data not loaded on the server."}), 500

    nearest = None
    min_dist = float('inf')
    for station in STATIONS_DATA:
        try:
            station_lat = station.get('lat') or station.get('latitude')
            station_lon = station.get('lon') or station.get('longitude')
            if station_lat and station_lon:
                dist = haversine_distance(lat, lon, float(station_lat), float(station_lon))
                if dist < min_dist:
                    min_dist = dist
                    nearest = station
        except (ValueError, TypeError):
            continue

    if nearest:
        nearest_for_frontend = {
            'name': nearest.get('name'),
            'id': nearest.get('stationId'),
            'latitude': nearest.get('lat'),
            'longitude': nearest.get('lon'),
        }
        return jsonify(nearest_for_frontend)
    else:
        return jsonify({"error": "No stations found."}), 404

# This is the IDF curves route, now correctly implemented
@app.route('/api/idf/curves', methods=['GET'])
def idf_curves():
    """
    Returns IDF curve data for a given station ID, formatted for plotting.
    """
    stationId = request.args.get('stationId')
    if not stationId:
        return jsonify({"error": "Missing 'stationId' parameter"}), 400

    idf_key = IDF_KEY_MAPPING.get(stationId)
    if not idf_key or idf_key not in IDF_DATA:
        print(f"IDF data not found for station ID: {stationId}")
        return jsonify({"error": "IDF data not found for this station."}), 404

    idf_station_data = IDF_DATA[idf_key]
    if not idf_station_data:
        return jsonify({"error": "No IDF data available for this station."}), 404

    # Group and sort the data on the backend to prevent frontend issues
    grouped_by_duration = {}
    for entry in idf_station_data:
        duration_str = entry.get('duration')
        duration_in_minutes = duration_to_minutes(duration_str)

        if duration_in_minutes is not None:
            if duration_in_minutes not in grouped_by_duration:
                grouped_by_duration[duration_in_minutes] = { 'duration': duration_in_minutes }

            for rp in ['2', '5', '10', '25', '50', '100']:
                intensity = entry.get(rp)
                if intensity is not None:
                    grouped_by_duration[duration_in_minutes][rp] = intensity

    # Convert the grouped data to a sorted list
    final_data_list = sorted(list(grouped_by_duration.values()), key=lambda x: x['duration'])
    
    return jsonify({
        "stationId": stationId,
        "data": final_data_list
    })

@app.route('/')
def index():
    return send_from_directory(
        r'C:\Users\moses\civil-eng-website\client\public', 'index.html'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)