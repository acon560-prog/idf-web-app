# File: server/app.py

import re
import json
import os
import math
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='../build', static_url_path='/')
CORS(app) # Enable CORS for all routes

# Define the provinces to load. Add more as you get the data for them.
PROVINCES = ['QC', 'ON', 'BC', 'AB', 'MB', 'SK', 'NB', 'NL', 'NS', 'PE', 'YT', 'NT', 'NU']

STATIONS_DATA = []
IDF_DATA = {}
IDF_KEY_MAPPING = {} 

for province_code in PROVINCES:
    # Construct file paths for each province.
    # Assumes your data is structured like this: data/QC/master...json
    stations_path = os.path.join(os.path.dirname(__file__), 'data', province_code, 'master_stations_enriched_validated.json')
    idf_path = os.path.join(os.path.dirname(__file__), 'data', province_code, 'idf_data_by_station.json')

    try:
        # Load station data
        with open(stations_path, 'r', encoding='utf-8') as f:
            STATIONS_DATA.extend(json.load(f))
        print(f"Successfully loaded stations metadata for {province_code}.")

        # Load IDF data and create mapping
        with open(idf_path, 'r', encoding='utf-8') as f:
            prov_idf_data = json.load(f)
            IDF_DATA.update(prov_idf_data)
            for key in prov_idf_data:
                # Use a more robust regex to find the station ID
                # This regex looks for a 7-digit number or a 3-digit number followed by 2 letters and 1 digit
                station_id_match = re.search(r'(\d{7}|\d{3}[A-Z]{2}\d)', key)
                if station_id_match:
                    station_id = station_id_match.group(1)
                    IDF_KEY_MAPPING[station_id] = key
                else:
                    # Fallback for keys that don't match the regex
                    IDF_KEY_MAPPING[key] = key
        print(f"Successfully loaded IDF data for {len(prov_idf_data)} stations in {province_code}.")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Could not load data for {province_code}: {e}")
        continue
print(f"Total stations loaded: {len(STATIONS_DATA)}")
print(f"Total IDF data sets loaded: {len(IDF_DATA)}")

def duration_to_minutes(duration_str):
    if not isinstance(duration_str, str):
        return None
    duration_str = duration_str.lower().strip()
    if 'min' in duration_str:
        return int(duration_str.replace('min', '').strip())
    elif 'h' in duration_str:
        return int(float(duration_str.replace('h', '').strip()) * 60)
    return None

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c
    
@app.route('/api/stations', methods=['GET'])
def get_stations():
    return jsonify(STATIONS_DATA)

@app.route('/api/nearest-station', methods=['GET'])
def nearest_station():
    try:
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid latitude or longitude."}), 400

    if not isinstance(STATIONS_DATA, list) or not STATIONS_DATA:
        return jsonify({"error": "Stations data not available."}), 500

    closest_station = None
    min_distance = float('inf')

    for station in STATIONS_DATA:
        station_lat = station.get('lat')
        station_lon = station.get('lon')

        if station_lat is not None and station_lon is not None:
            try:
                station_lat = float(station_lat)
                station_lon = float(station_lon)
                distance = haversine(lat, lon, station_lat, station_lon)

                if distance < min_distance:
                    min_distance = distance
                    closest_station = station

            except (ValueError, TypeError):
                continue

    if closest_station:
        return jsonify(closest_station)
    else:
        return jsonify({"error": "No stations with valid lat/lon found."}), 404

@app.route('/api/idf/curves', methods=['GET'])
def idf_curves():
    try:
        stationId = request.args.get('stationId')
        print(f"Received request for station ID: {stationId}")
        if not stationId:
            return jsonify({"error": "Missing 'stationId' parameter"}), 400

        idf_key = IDF_KEY_MAPPING.get(stationId)
        
        if not idf_key or idf_key not in IDF_DATA:
            print(f"IDF data not found for station ID: {stationId}")
            return jsonify({"error": "IDF data not found for this station."}), 404

        idf_station_data = IDF_DATA[idf_key]
        
        processed_data = []
        
        for entry in idf_station_data:
            duration_str = entry.get('duration')
            duration_in_minutes = duration_to_minutes(duration_str)

            if duration_in_minutes is not None:
                data_point = {
                    'duration': duration_in_minutes
                }
                for rp in ['2', '5', '10', '25', '50', '100']:
                    intensity = entry.get(rp)
                    if intensity is not None:
                        try:
                            data_point[rp] = float(intensity)
                        except (ValueError, TypeError):
                            continue
                
                if len(data_point) > 1:
                    processed_data.append(data_point)

        processed_data.sort(key=lambda x: x['duration'])
        
        return jsonify({"data": processed_data})

    except Exception as e:
        print(f"An unexpected error occurred in idf_curves: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)