# File: server/app.py

import re
import json
import os
import math
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
import certifi
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
from flask import send_from_directory

app = Flask(__name__, static_folder='build', static_url_path='')
default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
extra_origins = [
    origin.strip()
    for origin in (os.environ.get("FRONTEND_ORIGINS") or "").split(",")
    if origin.strip()
]
allowed_origins = default_origins + extra_origins

# Allow all Vercel preview domains automatically
allowed_origins.append(r"https://.*\.vercel\.app")

CORS(
    app,
    resources={r"/api/*": {"origins": allowed_origins}},
    supports_credentials=True,
)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    file_path = os.path.join(app.static_folder, path)
    if path and os.path.exists(file_path):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')
@app.errorhandler(404)
def handle_not_found(_error):
    if request.path.startswith("/api"):
        return jsonify({'error': 'Not Found'}), 404
    return send_from_directory(app.static_folder, 'index.html')

app.config['MONGO_URI'] = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/civispec')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'change-me')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
mongo = PyMongo(app, tlsCAFile=certifi.where())
# mongo = PyMongo(app)
jwt = JWTManager(app)

users_collection = mongo.db.users
submissions_collection = mongo.db.submissions
ADMIN_EMAIL = (os.environ.get('ADMIN_EMAIL') or '').strip().lower()

# Define the provinces to load. Add more as you get the data for them.
PROVINCES = ['QC', 'ON', 'BC', 'AB', 'MB', 'SK', 'NB', 'NL', 'NS', 'PE', 'YT', 'NT', 'NU']

STATIONS_DATA = []
STATION_LOOKUP = {}
IDF_DATA = {}
IDF_KEY_MAPPING = {}
IDF_STATION_IDS = set() 
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
RETURN_PERIODS = ('2', '5', '10', '25', '50', '100')
# Station IDs are usually either 7 digits or 3 digits + 4 alphanumeric chars.
STATION_ID_RE = re.compile(r'(\d{7}|\d{3}[A-Z0-9]{4})')
ICC_EXPORTS_DIRNAME = 'icc_exports'
ICC_DURATION_ROW_RE = re.compile(r'^\d+(\.\d+)?\s(min|h)$', re.IGNORECASE)
LOADED_ICC_EXPORT_DIRS = set()
IDF_CC_FACTORS_DIR = os.path.join(DATA_DIR, 'idf_cc_factors')
DEFAULT_CC_SCENARIO = 'ssp585'
IDF_CC_TRUTHY = {'1', 'true', 'yes', 'on'}
_IDF_CC_FACTORS_INDEX = None
_IDF_CC_FACTORS_CACHE = {}


def normalize_email(email: str) -> str:
    return email.strip().lower() if isinstance(email, str) else ''


def determine_role(user_doc) -> str:
    if not user_doc:
        return 'user'
    role = user_doc.get('role')
    if role:
        return role
    email = normalize_email(user_doc.get('email'))
    if email and email == ADMIN_EMAIL:
        return 'admin'
    return 'user'


def isoformat_or_none(value):
    if isinstance(value, datetime):
        if value.tzinfo:
            return value.isoformat()
        return value.replace(microsecond=0).isoformat() + 'Z'
    return None


def serialize_user(user_doc):
    if not user_doc:
        return None
    role = determine_role(user_doc)
    return {
        'id': str(user_doc['_id']),
        'email': user_doc.get('email'),
        'name': user_doc.get('name'),
        'subscriptionStatus': user_doc.get('subscriptionStatus', 'trialing'),
        'plan': user_doc.get('plan'),
        'trialStartsAt': isoformat_or_none(user_doc.get('trialStartsAt')),
        'trialEndsAt': isoformat_or_none(user_doc.get('trialEndsAt')),
        'stripeCustomerId': user_doc.get('stripeCustomerId'),
        'role': role,
    }


def serialize_submission(doc):
    if not doc:
        return None
    return {
        '_id': str(doc.get('_id')),
        'name': doc.get('name'),
        'email': doc.get('email'),
        'message': doc.get('message'),
        'sendCopy': bool(doc.get('sendCopy')),
        'createdAt': isoformat_or_none(doc.get('createdAt')) or isoformat_or_none(doc.get('date')),
        'date': isoformat_or_none(doc.get('date')) or isoformat_or_none(doc.get('createdAt')),
    }


def generate_tokens(user_doc):
    identity = str(user_doc['_id'])
    role = determine_role(user_doc)
    additional_claims = {
        'email': user_doc.get('email'),
        'subscriptionStatus': user_doc.get('subscriptionStatus', 'trialing'),
        'role': role,
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

    if status == 'trialing':
        if isinstance(trial_end, datetime):
            if now <= trial_end:
                return True
            users_collection.update_one(
                {'_id': user_doc['_id']},
                {'$set': {'subscriptionStatus': 'trial_expired', 'updatedAt': now}},
            )
            return False
        # Legacy users might not have a recorded trial end. Treat as active trial.
        return True

    return False


def log_submission_to_file(name, email, message):
    log_path = os.path.join(os.path.dirname(__file__), '..', 'submissions.log')
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.utcnow().isoformat()}] {name} <{email}>: {message}\n")
    except OSError as exc:
        print(f"Failed to write submission log: {exc}")


def send_contact_email(name, email, message, send_copy=False):
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASS')
    if not email_user or not email_pass:
        print("Email credentials not configured; skipping email dispatch.")
        return True

    msg_admin = EmailMessage()
    msg_admin['Subject'] = 'New Contact Form Submission'
    msg_admin['From'] = email_user
    msg_admin['To'] = email_user
    msg_admin.set_content(f"Name: {name}\nEmail: {email}\nMessage:\n{message}")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(email_user, email_pass)
            smtp.send_message(msg_admin)

            if send_copy:
                msg_user = EmailMessage()
                msg_user['Subject'] = 'We received your message!'
                msg_user['From'] = email_user
                msg_user['To'] = email
                msg_user.set_content(
                    f"Hi {name},\n\nThanks for contacting us. Here's what you sent:\n\n"
                    f"\"{message}\"\n\nWe'll get back to you soon.\n\n- Civispec Team"
                )
                smtp.send_message(msg_user)
    except Exception as exc:
        print(f"Failed to send contact email: {exc}")
        return False

    return True

def extract_station_id(raw_value):
    if not raw_value:
        return None
    match = STATION_ID_RE.search(str(raw_value).upper())
    return match.group(1) if match else None


def parse_duration_to_minutes(duration_value):
    if duration_value is None:
        return None

    if isinstance(duration_value, (int, float)):
        try:
            minutes = int(round(float(duration_value)))
            return minutes if minutes > 0 else None
        except (TypeError, ValueError):
            return None

    text = str(duration_value).strip().lower()
    match = re.match(
        r'^(\d+(?:\.\d+)?)\s*(min|mins|minute|minutes|h|hr|hrs|hour|hours)$',
        text,
    )
    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2)
    if unit.startswith('h'):
        value *= 60

    minutes = int(round(value))
    return minutes if minutes > 0 else None


def minutes_to_duration_label(minutes):
    if minutes % 60 == 0 and minutes >= 60:
        return f"{minutes // 60} h"
    return f"{minutes} min"


def normalize_idf_rows(rows):
    if not isinstance(rows, list):
        return []

    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue

        duration_minutes = parse_duration_to_minutes(row.get('duration'))
        if duration_minutes is None:
            continue

        normalized_row = {
            'duration': minutes_to_duration_label(duration_minutes),
        }
        for rp in RETURN_PERIODS:
            value = row.get(rp)
            if value in (None, '', -99.9, '-99.9'):
                continue
            try:
                normalized_row[rp] = float(value)
            except (TypeError, ValueError):
                continue

        if len(normalized_row) > 1:
            normalized.append(normalized_row)

    return normalized


def parse_icc_table_2a(lines):
    results = []
    in_table = False
    data_started = False

    for line in lines:
        if 'table 2a' in line.lower():
            in_table = True
            continue

        if not in_table:
            continue

        parts = line.strip().split()
        if len(parts) > 1:
            duration_token = f"{parts[0]} {parts[1]}"
        elif parts:
            duration_token = parts[0]
        else:
            duration_token = ''

        if not data_started:
            if ICC_DURATION_ROW_RE.match(duration_token):
                data_started = True
            else:
                continue

        if not ICC_DURATION_ROW_RE.match(duration_token):
            break

        if len(parts) < 8:
            continue

        if parts[1].lower() in ('min', 'h'):
            duration = f"{parts[0]} {parts[1]}"
            values = parts[2:-1]
        else:
            duration = parts[0]
            values = parts[1:-1]

        if len(values) < len(RETURN_PERIODS):
            continue

        parsed_row = {'duration': duration}
        for idx, rp in enumerate(RETURN_PERIODS):
            try:
                numeric_value = float(values[idx])
            except (TypeError, ValueError, IndexError):
                numeric_value = None
            if numeric_value == -99.9:
                numeric_value = None
            parsed_row[rp] = numeric_value

        results.append(parsed_row)

    return normalize_idf_rows(results)


def parse_icc_json_payload(payload, fallback_station_id=None):
    parsed = {}

    if isinstance(payload, dict):
        if isinstance(payload.get('data'), list):
            station_id = extract_station_id(payload.get('stationId')) or fallback_station_id
            rows = normalize_idf_rows(payload.get('data'))
            if station_id and rows:
                parsed[station_id] = rows
            return parsed

        for key, value in payload.items():
            if not isinstance(value, list):
                continue
            station_id = extract_station_id(key)
            if not station_id and fallback_station_id and len(payload) == 1:
                station_id = fallback_station_id
            rows = normalize_idf_rows(value)
            if station_id and rows:
                parsed[station_id] = rows
        return parsed

    if isinstance(payload, list):
        is_station_list = all(
            isinstance(item, dict)
            and item.get('stationId')
            and isinstance(item.get('data'), list)
            for item in payload
        )
        if is_station_list:
            for item in payload:
                station_id = extract_station_id(item.get('stationId'))
                rows = normalize_idf_rows(item.get('data'))
                if station_id and rows:
                    parsed[station_id] = rows
            return parsed

        rows = normalize_idf_rows(payload)
        if fallback_station_id and rows:
            parsed[fallback_station_id] = rows

    return parsed


def merge_station_idf_rows(station_id, rows):
    if not station_id or not rows:
        return 'skipped'

    existing_key = IDF_KEY_MAPPING.get(station_id)
    if existing_key and existing_key in IDF_DATA:
        existing_rows = IDF_DATA.get(existing_key) or []
        if existing_rows:
            return 'skipped'
        IDF_DATA[existing_key] = rows
        IDF_STATION_IDS.add(station_id)
        return 'updated'

    key_to_use = station_id
    if key_to_use in IDF_DATA and (IDF_DATA.get(key_to_use) or []):
        key_to_use = f"{station_id}__{ICC_EXPORTS_DIRNAME}"

    IDF_DATA[key_to_use] = rows
    IDF_KEY_MAPPING[station_id] = key_to_use
    IDF_STATION_IDS.add(station_id)
    return 'added'


def load_icc_exports_from_dir(directory_path):
    summary = {
        'processed': 0,
        'added': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0,
    }

    if not os.path.isdir(directory_path):
        return summary

    real_directory = os.path.realpath(directory_path)
    if real_directory in LOADED_ICC_EXPORT_DIRS:
        return summary

    LOADED_ICC_EXPORT_DIRS.add(real_directory)

    for file_name in sorted(os.listdir(directory_path)):
        file_path = os.path.join(directory_path, file_name)
        if not os.path.isfile(file_path):
            continue
        lower_name = file_name.lower()
        if not (lower_name.endswith('.txt') or lower_name.endswith('.json')):
            continue

        summary['processed'] += 1
        fallback_station_id = extract_station_id(file_name)

        try:
            station_data = {}
            if lower_name.endswith('.txt'):
                with open(file_path, 'r', encoding='latin-1', errors='ignore') as handle:
                    rows = parse_icc_table_2a(handle.readlines())
                if fallback_station_id and rows:
                    station_data[fallback_station_id] = rows
            else:
                with open(file_path, 'r', encoding='utf-8') as handle:
                    payload = json.load(handle)
                station_data = parse_icc_json_payload(payload, fallback_station_id=fallback_station_id)
        except (OSError, json.JSONDecodeError) as exc:
            summary['errors'] += 1
            print(f"Could not process ICC export file {file_path}: {exc}")
            continue

        if not station_data:
            summary['skipped'] += 1
            continue

        for station_id, rows in station_data.items():
            action = merge_station_idf_rows(station_id, rows)
            if action in summary:
                summary[action] += 1
            else:
                summary['skipped'] += 1

    return summary


for province_code in PROVINCES:
    # Assumes your data is structured like this:
    # data/QC/master_stations_enriched_validated.json and data/QC/idf_data_by_station.json.
    stations_path = os.path.join(DATA_DIR, province_code, 'master_stations_enriched_validated.json')
    idf_path = os.path.join(DATA_DIR, province_code, 'idf_data_by_station.json')

    try:
        with open(stations_path, 'r', encoding='utf-8') as f:
            stations = json.load(f)
            STATIONS_DATA.extend(stations)
            for station in stations:
                sid = station.get('stationId')
                if sid:
                    STATION_LOOKUP[sid] = station
        print(f"Successfully loaded stations metadata for {province_code}.")
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"Could not load stations metadata for {province_code}: {exc}")

    try:
        with open(idf_path, 'r', encoding='utf-8') as f:
            prov_idf_data = json.load(f)
            IDF_DATA.update(prov_idf_data)
            for key in prov_idf_data:
                station_id_match = extract_station_id(key)
                if station_id_match:
                    IDF_KEY_MAPPING[station_id_match] = key
                    IDF_STATION_IDS.add(station_id_match)
                else:
                    # Fallback for keys that don't have a recognizable station ID.
                    IDF_KEY_MAPPING[key] = key
                    IDF_STATION_IDS.add(key)
        print(f"Successfully loaded IDF data for {len(prov_idf_data)} stations in {province_code}.")
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"Could not load IDF JSON for {province_code}: {exc}")

    icc_dirs = (
        os.path.join(DATA_DIR, province_code, ICC_EXPORTS_DIRNAME),
        os.path.join(DATA_DIR, ICC_EXPORTS_DIRNAME, province_code),
        os.path.join(DATA_DIR, ICC_EXPORTS_DIRNAME),
    )
    for icc_dir in icc_dirs:
        summary = load_icc_exports_from_dir(icc_dir)
        if summary['processed'] or summary['errors']:
            print(
                f"Loaded ICC exports from {icc_dir}: "
                f"processed={summary['processed']}, added={summary['added']}, "
                f"updated={summary['updated']}, skipped={summary['skipped']}, errors={summary['errors']}"
            )

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


def _normalize_cc_scenario(raw_value):
    if raw_value is None:
        return DEFAULT_CC_SCENARIO

    scenario_text = str(raw_value).strip().lower()
    if not scenario_text:
        return DEFAULT_CC_SCENARIO

    scenario_key = re.sub(r'[^a-z0-9]', '', scenario_text)
    if scenario_key in {'none', 'baseline', 'off', 'false', '0'}:
        return None
    if scenario_key in {'ssp585', 'cc2050'}:
        return DEFAULT_CC_SCENARIO
    return scenario_text


def _parse_year_int(value):
    try:
        if value in (None, ''):
            return -1
        return int(value)
    except (TypeError, ValueError):
        return -1


def _coerce_float(value):
    try:
        if value in (None, ''):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _requested_cc_scenario(query_args):
    for flag_key in ('cc_2050', 'climateChange', 'applyClimateChange', 'apply_climate_change'):
        raw_flag = query_args.get(flag_key)
        if raw_flag is None:
            continue
        normalized_flag = str(raw_flag).strip().lower()
        if normalized_flag in IDF_CC_TRUTHY:
            return DEFAULT_CC_SCENARIO
        if normalized_flag in {'0', 'false', 'no', 'off'}:
            return None

    raw_scenario = (
        query_args.get('scenario')
        or query_args.get('climateScenario')
        or query_args.get('cc_scenario')
    )
    if raw_scenario is None:
        return None
    return _normalize_cc_scenario(raw_scenario)


def _idf_cc_factors_index():
    global _IDF_CC_FACTORS_INDEX
    if _IDF_CC_FACTORS_INDEX is not None:
        return _IDF_CC_FACTORS_INDEX

    index = {}
    loaded_files = 0

    if not os.path.isdir(IDF_CC_FACTORS_DIR):
        print(f"IDF_CC factors directory not found: {IDF_CC_FACTORS_DIR}")
        _IDF_CC_FACTORS_INDEX = index
        return _IDF_CC_FACTORS_INDEX

    for file_name in os.listdir(IDF_CC_FACTORS_DIR):
        if not file_name.lower().endswith('.json'):
            continue

        file_path = os.path.join(IDF_CC_FACTORS_DIR, file_name)
        try:
            with open(file_path, 'r', encoding='utf-8') as fp:
                payload = json.load(fp)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Skipping invalid IDF_CC factor file {file_path}: {exc}")
            continue

        station_id = extract_station_id(payload.get('stationId') or file_name)
        factors = payload.get('factors')
        if not station_id or not isinstance(factors, dict) or not factors:
            continue

        scenario = _normalize_cc_scenario(payload.get('scenario') or DEFAULT_CC_SCENARIO)
        if not scenario:
            continue

        station_factors = index.setdefault(station_id, {})
        candidate = {
            'path': file_path,
            'station_id': station_id,
            'scenario': scenario,
            'initial_year': _parse_year_int(payload.get('initialYear')),
            'final_year': _parse_year_int(payload.get('finalYear')),
        }
        current = station_factors.get(scenario)
        if (
            current is None
            or (candidate['final_year'], candidate['initial_year'], candidate['path'])
            > (current['final_year'], current['initial_year'], current['path'])
        ):
            station_factors[scenario] = candidate

        loaded_files += 1

    scenario_entries = sum(len(scenarios) for scenarios in index.values())
    print(
        f"Indexed IDF_CC factors from {IDF_CC_FACTORS_DIR}: "
        f"files={loaded_files}, station_scenarios={scenario_entries}"
    )
    _IDF_CC_FACTORS_INDEX = index
    return _IDF_CC_FACTORS_INDEX


def _load_idf_cc_factors(entry):
    if not entry:
        return {}
    file_path = entry.get('path')
    if not file_path:
        return {}

    cached = _IDF_CC_FACTORS_CACHE.get(file_path)
    if cached is not None:
        return cached

    try:
        with open(file_path, 'r', encoding='utf-8') as fp:
            payload = json.load(fp)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Failed to load IDF_CC factors from {file_path}: {exc}")
        payload = {}

    _IDF_CC_FACTORS_CACHE[file_path] = payload
    return payload


def find_nearest_station_with_idf_cc(station_id, scenario=DEFAULT_CC_SCENARIO):
    origin = STATION_LOOKUP.get(station_id)
    if not origin:
        return None

    scenario = _normalize_cc_scenario(scenario) or DEFAULT_CC_SCENARIO
    factors_index = _idf_cc_factors_index()
    if not factors_index:
        return None

    origin_lat = parse_coordinate(origin.get('lat'))
    origin_lon = parse_coordinate(origin.get('lon'))
    if origin_lat is None or origin_lon is None:
        return None

    best_station = None
    best_entry = None
    best_distance = float('inf')

    for candidate in STATIONS_DATA:
        candidate_id = candidate.get('stationId')
        if not candidate_id or candidate_id == station_id:
            continue

        candidate_scenarios = factors_index.get(candidate_id)
        if not candidate_scenarios:
            continue

        scenario_entry = candidate_scenarios.get(scenario)
        if not scenario_entry:
            continue

        cand_lat = parse_coordinate(candidate.get('lat'))
        cand_lon = parse_coordinate(candidate.get('lon'))
        if cand_lat is None or cand_lon is None:
            continue

        distance = haversine(origin_lat, origin_lon, cand_lat, cand_lon)
        if distance < best_distance:
            best_distance = distance
            best_station = candidate
            best_entry = scenario_entry

    if not best_station or not best_entry:
        return None

    return {
        'station': best_station,
        'entry': best_entry,
        'distance_km': best_distance,
    }


def apply_idf_cc_factors(rows, factors):
    if not isinstance(rows, list) or not rows:
        return rows, {'updated': 0, 'total': 0}
    if not isinstance(factors, dict) or not factors:
        return rows, {'updated': 0, 'total': 0}

    updated_rows = []
    updated_cells = 0
    total_cells = 0

    for row in rows:
        row_out = dict(row)
        duration_key = str(row.get('duration'))
        factor_row = factors.get(duration_key)
        if not isinstance(factor_row, dict):
            updated_rows.append(row_out)
            continue

        for rp in RETURN_PERIODS:
            raw_base = row_out.get(rp)
            if not isinstance(raw_base, (int, float)):
                continue
            total_cells += 1
            factor_value = _coerce_float(factor_row.get(rp))
            if factor_value is None:
                continue
            row_out[rp] = float(raw_base) * factor_value
            updated_cells += 1

        updated_rows.append(row_out)

    return updated_rows, {'updated': updated_cells, 'total': total_cells}


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
    role = 'admin' if email and email == ADMIN_EMAIL else 'user'

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
        'role': role,
    }

    result = users_collection.insert_one(user_doc)
    user_doc['_id'] = result.inserted_id
    user_doc['role'] = role

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

    role = determine_role(user_doc)
    updates = {'updatedAt': datetime.utcnow()}
    if user_doc.get('role') != role:
        updates['role'] = role
    user_doc['role'] = role

    users_collection.update_one(
        {'_id': user_doc['_id']},
        {'$set': updates},
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


@app.route('/api/contact', methods=['POST'])
def submit_contact():
    payload = request.get_json() or {}
    name = (payload.get('name') or '').strip()
    email = (payload.get('email') or '').strip()
    message = (payload.get('message') or '').strip()
    send_copy = bool(payload.get('sendCopy'))
    honeypot = (payload.get('honeypot') or '').strip()

    if honeypot:
        return jsonify({'success': False, 'message': 'Spam detected.'}), 400

    if not name or not email or not message:
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400

    log_submission_to_file(name, email, message)

    submission_doc = {
        'name': name,
        'email': email,
        'message': message,
        'sendCopy': send_copy,
        'createdAt': datetime.utcnow(),
        'date': datetime.utcnow(),
    }

    try:
        submissions_collection.insert_one(submission_doc)
    except Exception as exc:
        print(f"Failed to persist contact submission: {exc}")

    email_ok = send_contact_email(name, email, message, send_copy=send_copy)

    if not email_ok:
        return jsonify({'success': False, 'message': 'Submission saved, but email could not be sent.'}), 202

    return jsonify({'success': True})


@app.route('/api/contact', methods=['GET'])
@jwt_required()
def list_contact_submissions():
    user_doc = get_current_user()
    if not user_doc or determine_role(user_doc) != 'admin':
        return jsonify({'error': 'Forbidden'}), 403

    try:
        cursor = submissions_collection.find().sort([('date', -1), ('createdAt', -1)])
        submissions = [s for s in (serialize_submission(doc) for doc in cursor) if s]
        return jsonify(submissions)
    except Exception as exc:
        print(f"Failed to fetch submissions: {exc}")
        return jsonify({'error': 'Failed to fetch submissions'}), 500


def duration_to_minutes(duration_str):
    return parse_duration_to_minutes(duration_str)

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
        stationId = str(stationId)

        climate_scenario = _requested_cc_scenario(request.args)
        if climate_scenario:
            print(f"Climate change scenario requested: {climate_scenario}")

        idf_key = IDF_KEY_MAPPING.get(stationId)
        fallback_meta = None
        climate_adjustment_meta = None
        
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

        if climate_scenario:
            scenario_key = _normalize_cc_scenario(climate_scenario) or DEFAULT_CC_SCENARIO
            idf_station_id = str(fallback_meta['usedStationId']) if fallback_meta else stationId
            factor_station = STATION_LOOKUP.get(idf_station_id)
            factor_index = _idf_cc_factors_index()
            factor_entry = (factor_index.get(idf_station_id) or {}).get(scenario_key)
            factor_fallback = None

            if not factor_entry:
                nearest_with_factors = find_nearest_station_with_idf_cc(idf_station_id, scenario=scenario_key)
                if nearest_with_factors:
                    factor_station = nearest_with_factors['station']
                    factor_entry = nearest_with_factors['entry']
                    factor_fallback = {
                        'requestedStationId': idf_station_id,
                        'requestedStationName': STATION_LOOKUP.get(idf_station_id, {}).get('name'),
                        'usedStationId': factor_station.get('stationId'),
                        'usedStationName': factor_station.get('name'),
                        'distanceKm': round(nearest_with_factors['distance_km'], 2),
                    }

            climate_adjustment_meta = {
                'requested': True,
                'scenario': scenario_key,
                'requestedStationId': stationId,
                'idfStationId': idf_station_id,
                'applied': False,
            }

            if factor_entry:
                factor_doc = _load_idf_cc_factors(factor_entry)
                factors = factor_doc.get('factors') or {}
                processed_data, summary = apply_idf_cc_factors(processed_data, factors)
                climate_adjustment_meta.update({
                    'applied': True,
                    'factorStationId': (
                        factor_station.get('stationId')
                        if isinstance(factor_station, dict)
                        else factor_entry.get('station_id')
                    ),
                    'factorStationName': (
                        factor_station.get('name')
                        if isinstance(factor_station, dict)
                        else None
                    ),
                    'sourceFile': (
                        factor_doc.get('sourceFile')
                        or os.path.basename(factor_entry.get('path', ''))
                    ),
                    'updatedCells': summary.get('updated', 0),
                    'candidateCells': summary.get('total', 0),
                })
                if factor_fallback:
                    climate_adjustment_meta['factorFallback'] = factor_fallback
            else:
                climate_adjustment_meta['reason'] = (
                    f"No {scenario_key} factors found for this station or nearby stations."
                )
        
        response_payload = {"data": processed_data}
        if fallback_meta:
            response_payload['fallback'] = fallback_meta
        if climate_adjustment_meta:
            response_payload['climateAdjustment'] = climate_adjustment_meta
        return jsonify(response_payload)

    except Exception as e:
        print(f"An unexpected error occurred in idf_curves: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    #app.run(debug=True, port=5000)