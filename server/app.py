# File: server/app.py

import re
import json
import os
import math
from datetime import datetime, timedelta

import bcrypt
from bson import ObjectId
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)
from flask_pymongo import PyMongo

app = Flask(__name__, static_folder='../build', static_url_path='/')
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:3000", "http://127.0.0.1:3000"]}}, supports_credentials=True)

app.config['MONGO_URI'] = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/civispec')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'change-me')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

mongo = PyMongo(app)
jwt = JWTManager(app)

users_collection = mongo.db.users

# Define the provinces to load. Add more as you get the data for them.
PROVINCES = ['QC', 'ON', 'BC', 'AB', 'MB', 'SK', 'NB', 'NL', 'NS', 'PE', 'YT', 'NT', 'NU']

STATIONS_DATA = []
STATION_LOOKUP = {}
IDF_DATA = {}
IDF_KEY_MAPPING = {}
IDF_STATION_IDS = set() 


def normalize_email(email: str) -> str:
    return email.strip().lower() if isinstance(email, str) else ''


def isoformat_or_none(value):
    if isinstance(value, datetime):
        if value.tzinfo:
            return value.isoformat()
        return value.replace(microsecond=0).isoformat() + 'Z'
    return None


def serialize_user(user_doc):
    if not user_doc:
        return None
    return {
        'id': str(user_doc['_id']),
        'email': user_doc.get('email'),
        'name': user_doc.get('name'),
        'subscriptionStatus': user_doc.get('subscriptionStatus', 'trialing'),
        'plan': user_doc.get('plan'),
        'trialStartsAt': isoformat_or_none(user_doc.get('trialStartsAt')),
        'trialEndsAt': isoformat_or_none(user_doc.get('trialEndsAt')),
        'stripeCustomerId': user_doc.get('stripeCustomerId'),
    }


def generate_tokens(user_doc):
    identity = str(user_doc['_id'])
    additional_claims = {
        'email': user_doc.get('email'),
        'subscriptionStatus': user_doc.get('subscriptionStatus', 'trialing'),
    }
    access_token = create_access_token(identity=identity, additional_claims=additional_claims)
    refresh_token = create_refresh_token(identity=identity)
    return {
        'accessToken': access_token,
        'refreshToken': refresh_token,
    }


def get_user_by_id(user_id):
    try:
        return users_collection.find_one({'_id': ObjectId(user_id)})
    except Exception:
        return None


def get_current_user():
    identity = get_jwt_identity()
    if not identity:
        return None
    return get_user_by_id(identity)


def user_has_active_access(user_doc):
    if not user_doc:
        return False

    status = user_doc.get('subscriptionStatus')
    if status == 'active':
        return True

    trial_end = user_doc.get('trialEndsAt')
    now = datetime.utcnow()

    if status == 'trialing' and isinstance(trial_end, datetime):
        if now <= trial_end:
            return True
        users_collection.update_one(
            {'_id': user_doc['_id']},
            {'$set': {'subscriptionStatus': 'trial_expired', 'updatedAt': now}},
        )
        return False

    return False

for province_code in PROVINCES:
    # Construct file paths for each province.
    # Assumes your data is structured like this: data/QC/master...json
    stations_path = os.path.join(os.path.dirname(__file__), 'data', province_code, 'master_stations_enriched_validated.json')
    idf_path = os.path.join(os.path.dirname(__file__), 'data', province_code, 'idf_data_by_station.json')

    try:
        # Load station data
        with open(stations_path, 'r', encoding='utf-8') as f:
            stations = json.load(f)
            STATIONS_DATA.extend(stations)
            for station in stations:
                sid = station.get('stationId')
                if sid:
                    STATION_LOOKUP[sid] = station
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
                    IDF_STATION_IDS.add(station_id)
                else:
                    # Fallback for keys that don't match the regex
                    IDF_KEY_MAPPING[key] = key
                    IDF_STATION_IDS.add(key)
        print(f"Successfully loaded IDF data for {len(prov_idf_data)} stations in {province_code}.")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Could not load data for {province_code}: {e}")
        continue
print(f"Total stations loaded: {len(STATIONS_DATA)}")
print(f"Total IDF data sets loaded: {len(IDF_DATA)}")


def parse_coordinate(value):
    try:
        if value in (None, ''):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def find_nearest_station_with_idf(station_id):
    origin = STATION_LOOKUP.get(station_id)
    if not origin:
        return None

    origin_lat = parse_coordinate(origin.get('lat'))
    origin_lon = parse_coordinate(origin.get('lon'))
    if origin_lat is None or origin_lon is None:
        return None

    best_station = None
    best_idf_key = None
    best_distance = float('inf')

    for candidate in STATIONS_DATA:
        candidate_id = candidate.get('stationId')
        if not candidate_id or candidate_id not in IDF_KEY_MAPPING:
            continue
        if candidate_id == station_id:
            continue

        cand_lat = parse_coordinate(candidate.get('lat'))
        cand_lon = parse_coordinate(candidate.get('lon'))
        if cand_lat is None or cand_lon is None:
            continue

        distance = haversine(origin_lat, origin_lon, cand_lat, cand_lon)
        if distance < best_distance:
            best_distance = distance
            best_station = candidate
            best_idf_key = IDF_KEY_MAPPING[candidate_id]

    if not best_station or best_idf_key is None:
        return None

    return {
        'station': best_station,
        'idf_key': best_idf_key,
        'distance_km': best_distance
    }


@app.route('/api/auth/register', methods=['POST'])
def register():
    payload = request.get_json() or {}
    email = normalize_email(payload.get('email'))
    username = payload.get('username')
    password = payload.get('password')
    name = payload.get('name', '')

    if not password:
        return jsonify({'error': 'Password is required.'}), 400

    if email:
        if users_collection.find_one({'email': email}):
            return jsonify({'error': 'An account with this email already exists.'}), 409
    if username:
        if users_collection.find_one({'username': username}):
            return jsonify({'error': 'An account with this username already exists.'}), 409

    if not email and not username:
        return jsonify({'error': 'An email or username is required.'}), 400

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    now = datetime.utcnow()
    trial_end = now + timedelta(days=7)

    user_doc = {
        'email': email if email else None,
        'username': username if username else None,
        'name': name,
        'passwordHash': password_hash,
        'subscriptionStatus': 'trialing',
        'plan': None,
        'stripeCustomerId': None,
        'trialStartsAt': now,
        'trialEndsAt': trial_end,
        'createdAt': now,
        'updatedAt': now,
    }

    result = users_collection.insert_one(user_doc)
    user_doc['_id'] = result.inserted_id

    tokens = generate_tokens(user_doc)

    return jsonify({
        'user': serialize_user(user_doc),
        **tokens,
    }), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    payload = request.get_json() or {}
    identifier = payload.get('email') or payload.get('username')
    password = payload.get('password')

    if not identifier or not password:
        return jsonify({'error': 'Email/username and password are required.'}), 400

    email = normalize_email(identifier) if '@' in str(identifier) else None

    if email:
        query = {'email': email}
    else:
        query = {'username': identifier}

    user_doc = users_collection.find_one(query)
    if not user_doc or 'passwordHash' not in user_doc:
        return jsonify({'error': 'Invalid credentials.'}), 401

    stored_hash = user_doc['passwordHash']
    if isinstance(stored_hash, bytes):
        stored_hash = stored_hash.decode('utf-8')

    if not bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
        return jsonify({'error': 'Invalid email or password.'}), 401

    users_collection.update_one(
        {'_id': user_doc['_id']},
        {'$set': {'updatedAt': datetime.utcnow()}},
    )

    tokens = generate_tokens(user_doc)

    return jsonify({
        'user': serialize_user(user_doc),
        **tokens,
    })


@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def auth_me():
    user_doc = get_current_user()
    if not user_doc:
        return jsonify({'error': 'User not found.'}), 404
    return jsonify({'user': serialize_user(user_doc)})


@app.route('/api/auth/refresh-token', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    user_doc = get_current_user()
    if not user_doc:
        return jsonify({'error': 'User not found.'}), 404

    additional_claims = {
        'email': user_doc.get('email'),
        'subscriptionStatus': user_doc.get('subscriptionStatus', 'trialing'),
    }
    access_token = create_access_token(identity=str(user_doc['_id']), additional_claims=additional_claims)

    return jsonify({'accessToken': access_token})

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
        station_with_distance = dict(closest_station)
        if min_distance != float('inf'):
            station_with_distance['distance_km'] = round(min_distance, 2)
        return jsonify(station_with_distance)
    else:
        return jsonify({"error": "No stations with valid lat/lon found."}), 404

@app.route('/api/idf/curves', methods=['GET'])
@jwt_required()
def idf_curves():
    user_doc = get_current_user()
    if not user_doc:
        return jsonify({'error': 'Authentication required.'}), 401

    if not user_has_active_access(user_doc):
        return jsonify({
            'error': 'Your free trial has expired. Please subscribe to continue accessing IDF data.',
            'code': 'trial_expired',
        }), 402

    try:
        stationId = request.args.get('stationId')
        print(f"Received request for station ID: {stationId}")
        if not stationId:
            return jsonify({"error": "Missing 'stationId' parameter"}), 400

        idf_key = IDF_KEY_MAPPING.get(stationId)
        fallback_meta = None
        
        if not idf_key or idf_key not in IDF_DATA:
            print(f"IDF data not found for station ID: {stationId}. Attempting fallback.")
            fallback = find_nearest_station_with_idf(stationId)
            if fallback:
                fallback_station = fallback['station']
                idf_key = fallback['idf_key']
                fallback_meta = {
                    'requestedStationId': stationId,
                    'requestedStationName': STATION_LOOKUP.get(stationId, {}).get('name'),
                    'usedStationId': fallback_station.get('stationId'),
                    'usedStationName': fallback_station.get('name'),
                    'distanceKm': round(fallback['distance_km'], 2)
                }
                print(f"Fallback succeeded: using station {fallback_meta['usedStationId']} ({fallback_meta['usedStationName']}) at {fallback_meta['distanceKm']} km.")
            else:
                print(f"IDF fallback failed for station ID: {stationId}")
                return jsonify({"error": "IDF data not found for this station or nearby stations."}), 404
        
        idf_station_data = IDF_DATA.get(idf_key, [])

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
        
        response_payload = {"data": processed_data}
        if fallback_meta:
            response_payload['fallback'] = fallback_meta
        return jsonify(response_payload)

    except Exception as e:
        print(f"An unexpected error occurred in idf_curves: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)