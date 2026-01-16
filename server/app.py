# File: server/app.py

import re
import json
import os
import math
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

import bcrypt
import stripe
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

mongo = PyMongo(app)
jwt = JWTManager(app)

users_collection = mongo.db.users
submissions_collection = mongo.db.submissions
ADMIN_EMAIL = (os.environ.get('ADMIN_EMAIL') or '').strip().lower()

# Stripe config (required for card-based trials)
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_CONSULTANT_MONTHLY = os.environ.get("STRIPE_PRICE_CONSULTANT_MONTHLY")
STRIPE_PRICE_MUNICIPAL_ANNUAL = os.environ.get("STRIPE_PRICE_MUNICIPAL_ANNUAL")
FRONTEND_URL = (os.environ.get("FRONTEND_URL") or "http://localhost:3000").rstrip("/")
STRIPE_TRIAL_VERIFICATION_AMOUNT_CENTS = int(os.environ.get("STRIPE_TRIAL_VERIFICATION_AMOUNT_CENTS") or "100")
STRIPE_CURRENCY = (os.environ.get("STRIPE_CURRENCY") or "cad").lower().strip()

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# Define the provinces to load. Add more as you get the data for them.
PROVINCES = ['QC', 'ON', 'BC', 'AB', 'MB', 'SK', 'NB', 'NL', 'NS', 'PE', 'YT', 'NT', 'NU']

STATIONS_DATA = []
STATION_LOOKUP = {}
IDF_DATA = {}
IDF_KEY_MAPPING = {}
IDF_STATION_IDS = set() 


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
        'trialUsed': bool(user_doc.get('trialUsed')),
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
        # If trial end is unknown, treat as expired for safety (no free access without an end date).
        users_collection.update_one(
            {'_id': user_doc['_id']},
            {'$set': {'subscriptionStatus': 'trial_expired', 'updatedAt': now}},
        )
        return False

    return False

def trial_already_used(user_doc) -> bool:
    """
    One-trial-per-email enforcement.
    Treat any existing trial history as "used", even if legacy documents don't have trialUsed flag.
    """
    if not user_doc:
        return False
    if user_doc.get('trialUsed') is True:
        return True
    if isinstance(user_doc.get('trialStartsAt'), datetime):
        return True
    if user_doc.get('subscriptionStatus') in ('trialing', 'trial_expired', 'active', 'canceled', 'past_due', 'incomplete'):
        # If they've ever had a subscription lifecycle state recorded, don't grant another trial.
        return True
    return False

def ensure_user_indexes():
    try:
        users_collection.create_index('email', unique=True, sparse=True)
    except Exception as exc:
        print(f"Failed to ensure user indexes: {exc}")

ensure_user_indexes()


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
    role = 'admin' if email and email == ADMIN_EMAIL else 'user'

    user_doc = {
        'email': email if email else None,
        'username': username if username else None,
        'name': name,
        'passwordHash': password_hash,
        # Trial is started only after card collection via Stripe Checkout.
        'subscriptionStatus': 'trial_pending',
        'plan': None,
        'stripeCustomerId': None,
        'trialUsed': False,
        'trialStartsAt': None,
        'trialEndsAt': None,
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


def _price_id_for_plan(plan: str):
    plan = (plan or "").strip().lower()
    if plan in ("consultant", "consultant_monthly", "monthly"):
        return STRIPE_PRICE_CONSULTANT_MONTHLY, "consultant_monthly"
    if plan in ("municipal", "municipal_annual", "annual"):
        return STRIPE_PRICE_MUNICIPAL_ANNUAL, "municipal_annual"
    return None, None


@app.route('/api/billing/create-checkout-session', methods=['POST'])
@jwt_required()
def create_checkout_session():
    """
    Creates a Stripe Checkout session for a paid subscription (no trial).
    Trial access is started separately via the $1 refundable card verification flow.
    """
    if not STRIPE_SECRET_KEY:
        return jsonify({'error': 'Stripe is not configured.'}), 500

    user_doc = get_current_user()
    if not user_doc:
        return jsonify({'error': 'Authentication required.'}), 401

    payload = request.get_json() or {}
    plan = payload.get('plan') or 'consultant_monthly'
    price_id, plan_key = _price_id_for_plan(plan)
    if plan_key is None:
        return jsonify({'error': f'Unknown plan: {plan}'}), 400
    if not price_id:
        return jsonify({'error': f'Missing Stripe price ID for plan: {plan_key}'}), 500

    email = normalize_email(user_doc.get('email'))
    if not email:
        return jsonify({'error': 'A valid email is required for billing.'}), 400

    success_url = f"{FRONTEND_URL}/start?checkout=success"
    cancel_url = f"{FRONTEND_URL}/?checkout=cancel"

    customer_id = user_doc.get("stripeCustomerId")
    session_kwargs = {
        "mode": "subscription",
        "client_reference_id": str(user_doc["_id"]),
        "line_items": [{"price": price_id, "quantity": 1}],
        "subscription_data": {
            "metadata": {
                "userId": str(user_doc["_id"]),
                "plan": plan_key,
            },
        },
        "payment_method_collection": "always",
        "allow_promotion_codes": True,
        "success_url": success_url,
        "cancel_url": cancel_url,
    }

    # Reuse an existing Stripe customer if available (e.g., after card verification)
    if customer_id:
        session_kwargs["customer"] = customer_id
    else:
        session_kwargs["customer_email"] = email

    session = stripe.checkout.Session.create(
        **session_kwargs,
    )

    return jsonify({"url": session.url})


@app.route('/api/billing/create-trial-verification-session', methods=['POST'])
@jwt_required()
def create_trial_verification_session():
    """
    Creates a Stripe Checkout session to verify a card with a $1 refundable payment.
    After successful payment, we refund the $1 and start a 7-day trial.
    """
    if not STRIPE_SECRET_KEY:
        return jsonify({'error': 'Stripe is not configured.'}), 500

    user_doc = get_current_user()
    if not user_doc:
        return jsonify({'error': 'Authentication required.'}), 401

    if trial_already_used(user_doc):
        return jsonify({'error': 'Trial already used for this account.'}), 409

    email = normalize_email(user_doc.get('email'))
    if not email:
        return jsonify({'error': 'A valid email is required for billing.'}), 400

    success_url = f"{FRONTEND_URL}/start?trial=success"
    cancel_url = f"{FRONTEND_URL}/?trial=cancel"

    session = stripe.checkout.Session.create(
        mode="payment",
        customer_creation="always",
        customer_email=email,
        client_reference_id=str(user_doc["_id"]),
        payment_intent_data={
            # Save payment method for later subscription checkout.
            "setup_future_usage": "off_session",
            "metadata": {
                "userId": str(user_doc["_id"]),
                "purpose": "trial_verification",
            },
        },
        metadata={
            "userId": str(user_doc["_id"]),
            "purpose": "trial_verification",
        },
        line_items=[
            {
                "price_data": {
                    "currency": STRIPE_CURRENCY,
                    "unit_amount": STRIPE_TRIAL_VERIFICATION_AMOUNT_CENTS,
                    "product_data": {"name": "Trial verification (refunded)"},
                },
                "quantity": 1,
            }
        ],
        success_url=success_url,
        cancel_url=cancel_url,
    )

    return jsonify({"url": session.url})


@app.route('/api/billing/stripe-webhook', methods=['POST'])
def stripe_webhook():
    """
    Stripe webhook handler to sync subscription/trial status to MongoDB.
    """
    if not STRIPE_WEBHOOK_SECRET:
        return jsonify({'error': 'Stripe webhook secret not configured.'}), 500

    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as exc:
        print(f"Stripe webhook verification failed: {exc}")
        return jsonify({'error': 'Invalid signature'}), 400

    event_type = event.get("type")
    data_object = (event.get("data") or {}).get("object") or {}
    now = datetime.utcnow()

    def _update_user_by_email_or_id(user_id: str | None, email: str | None, updates: dict):
        query = None
        if user_id:
            try:
                query = {"_id": ObjectId(user_id)}
            except Exception:
                query = None
        if not query and email:
            query = {"email": normalize_email(email)}
        if not query:
            return
        users_collection.update_one(query, {"$set": {**updates, "updatedAt": now}})

    try:
        if event_type == "checkout.session.completed":
            # Checkout session includes the subscription and customer IDs.
            session = data_object
            metadata = session.get("metadata") or {}
            purpose = (metadata.get("purpose") or "").strip().lower()

            # Trial verification checkout (mode=payment)
            if purpose == "trial_verification":
                customer_id = session.get("customer")
                email = session.get("customer_details", {}).get("email") or session.get("customer_email")
                user_id = session.get("client_reference_id") or metadata.get("userId")
                payment_intent_id = session.get("payment_intent")

                # Refund the verification payment (idempotent by event id).
                if payment_intent_id:
                    try:
                        stripe.Refund.create(
                            payment_intent=payment_intent_id,
                            idempotency_key=event.get("id"),
                        )
                    except Exception as refund_exc:
                        print(f"Failed to refund trial verification payment: {refund_exc}")

                trial_start = now
                trial_end = now + timedelta(days=7)

                updates = {
                    "stripeCustomerId": customer_id,
                    "subscriptionStatus": "trialing",
                    "trialStartsAt": trial_start,
                    "trialEndsAt": trial_end,
                    "trialUsed": True,
                    "updatedAt": now,
                }
                _update_user_by_email_or_id(user_id, email, updates)
                return jsonify({'received': True})

            subscription_id = session.get("subscription")
            customer_id = session.get("customer")
            email = session.get("customer_details", {}).get("email") or session.get("customer_email")
            user_id = session.get("client_reference_id")

            trial_start = None
            trial_end = None
            subscription_status = None
            plan_key = None

            if subscription_id:
                sub = stripe.Subscription.retrieve(subscription_id)
                subscription_status = sub.get("status")
                trial_start_unix = sub.get("trial_start")
                trial_end_unix = sub.get("trial_end")
                if trial_start_unix:
                    trial_start = datetime.utcfromtimestamp(trial_start_unix)
                if trial_end_unix:
                    trial_end = datetime.utcfromtimestamp(trial_end_unix)
                plan_key = (sub.get("metadata") or {}).get("plan")

            updates = {
                "stripeCustomerId": customer_id,
                "stripeSubscriptionId": subscription_id,
                "plan": plan_key,
                "subscriptionStatus": subscription_status or "active",
            }

            # Mark trial as used if a trial was granted (or if it was ever started).
            if trial_end:
                updates["trialStartsAt"] = trial_start or now
                updates["trialEndsAt"] = trial_end
                updates["trialUsed"] = True
                # If Stripe says trialing, keep it; otherwise it might already be active.
                if updates["subscriptionStatus"] == "trialing":
                    pass
            else:
                # No trial on this checkout (e.g., user already used it)
                updates["trialUsed"] = True if trial_already_used(get_user_by_id(user_id) if user_id else None) else bool(
                    updates.get("trialUsed")
                )

            _update_user_by_email_or_id(user_id, email, updates)

        elif event_type in ("customer.subscription.updated", "customer.subscription.deleted", "customer.subscription.created"):
            sub = data_object
            customer_id = sub.get("customer")
            subscription_id = sub.get("id")
            status = sub.get("status")
            trial_start_unix = sub.get("trial_start")
            trial_end_unix = sub.get("trial_end")
            plan_key = (sub.get("metadata") or {}).get("plan")

            updates = {
                "stripeCustomerId": customer_id,
                "stripeSubscriptionId": subscription_id,
                "subscriptionStatus": status,
                "plan": plan_key,
            }

            if trial_start_unix:
                updates["trialStartsAt"] = datetime.utcfromtimestamp(trial_start_unix)
            if trial_end_unix:
                updates["trialEndsAt"] = datetime.utcfromtimestamp(trial_end_unix)
                updates["trialUsed"] = True

            users_collection.update_one(
                {"stripeCustomerId": customer_id},
                {"$set": {**updates, "updatedAt": now}},
            )

    except Exception as exc:
        print(f"Stripe webhook handler error ({event_type}): {exc}")
        return jsonify({'error': 'Webhook handler error'}), 500

    return jsonify({'received': True})


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
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    #app.run(debug=True, port=5000)