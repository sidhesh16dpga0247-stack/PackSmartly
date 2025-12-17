import json
import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

# --------------------------------------------------
# App setup
# --------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, 'app.db')

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret-change-me')

# --------------------------------------------------
# Database helpers
# --------------------------------------------------
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --------------------------------------------------
# Login required decorator
# --------------------------------------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

# --------------------------------------------------
# DESTINATION LOGIC (SCALABLE – 200+ supported)
# --------------------------------------------------
BEACH = {"goa", "bali", "maldives", "phuket", "miami", "ibiza", "seychelles"}
COLD = {"manali", "leh", "oslo", "helsinki", "reykjavik", "zurich"}
METRO = {"new york", "london", "tokyo", "paris", "dubai", "singapore", "hong kong"}
DESERT = {"dubai", "doha", "riyadh", "jaisalmer"}
ADVENTURE = {"leh", "manali", "queenstown", "interlaken", "patagonia"}
RELIGIOUS = {"varanasi", "mecca", "medina", "jerusalem", "amritsar"}

DEFAULT_ACTIVITIES = [
    "Sightseeing", "Shopping", "Photography",
    "Nightlife", "Museum Tour", "Local Food Tour",
    "Walking Tour", "Cultural Exploration", "Relaxation", "City Exploration"
]

def get_activities_for_destination(destination):
    d = destination.lower()

    if d in BEACH:
        return [
            "Swimming", "Beach Day", "Snorkeling", "Photography", "Nightlife",
            "Boat Ride", "Sunbathing", "Shopping", "Local Food Tour", "Relaxation"
        ]

    if d in COLD:
        return [
            "Hiking", "Camping", "Photography", "Snow Walk",
            "Adventure Sports", "Sightseeing", "Local Food Tour",
            "Bonfire", "Mountain Exploration", "Nature Walk"
        ]

    if d in METRO:
        return [
            "Sightseeing", "Museum Tour", "Shopping", "Business",
            "Nightlife", "Photography", "Local Food Tour",
            "Walking Tour", "Cultural Exploration", "City Exploration"
        ]

    if d in DESERT:
        return [
            "Desert Safari", "Photography", "Sightseeing",
            "Cultural Exploration", "Shopping", "Local Food Tour",
            "Adventure Sports", "Relaxation", "Camel Ride", "Nightlife"
        ]

    if d in ADVENTURE:
        return [
            "Hiking", "Camping", "Adventure Sports", "Photography",
            "Nature Walk", "Road Trip", "Mountain Exploration",
            "Bonfire", "Sightseeing", "Local Food Tour"
        ]

    if d in RELIGIOUS:
        return [
            "Temple Visit", "Sightseeing", "Walking Tour",
            "Cultural Exploration", "Photography", "Meditation",
            "Local Food Tour", "Shopping", "Relaxation", "City Exploration"
        ]

    return DEFAULT_ACTIVITIES

# --------------------------------------------------
# WEATHER LOGIC
# --------------------------------------------------
def get_weather(destination):
    d = destination.lower()
    if d in BEACH or d in DESERT:
        return "hot"
    if d in COLD:
        return "cold"
    return "normal"

# --------------------------------------------------
# PACKING LIST LOGIC (UNCHANGED & WORKING)
# --------------------------------------------------
def generate_packing_list(destination, duration, activities):
    base_items = {
        "Essentials": ["Phone", "Charger", "Wallet", "Passport", "Travel Tickets"],
        "Clothing": ["Underwear", "Socks", "T-Shirts", "Pants", "Jacket"],
        "Toiletries": ["Toothbrush", "Toothpaste", "Deodorant", "Soap"],
    }

    activity_items = {
        "Swimming": ["Swimsuit", "Towel", "Flip-flops"],
        "Hiking": ["Hiking Shoes", "Backpack", "Water Bottle"],
        "Camping": ["Tent", "Sleeping Bag", "Flashlight"],
        "Business": ["Formal Shirt", "Laptop", "Notebook"],
        "Photography": ["Camera", "Extra Batteries"],
        "Beach Day": ["Sunscreen", "Sandals", "Beach Bag"],
        "Shopping": ["Reusable Bags", "Wallet"],
        "Nightlife": ["Smart Casual Clothes", "Perfume"],
        "Museum Tour": ["Notebook", "Comfortable Shoes"],
        "Adventure Sports": ["Helmet", "Gloves"],
        "Road Trip": ["Car Charger", "Neck Pillow"],
        "Desert Safari": ["Scarf", "Sunscreen"],
    }

    generated = {k: list(v) for k, v in base_items.items()}

    for act in activities:
        if act in activity_items:
            generated.setdefault("Activity Gear", []).extend(activity_items[act])

    try:
        days = max(1, int(duration))
    except:
        days = 1

    generated["Clothing"].append(f"{days} pairs of socks")
    generated["Clothing"].append(f"{days} sets of underwear")

    weather = get_weather(destination)
    if weather == "hot":
        generated.setdefault("Weather Gear", []).extend(["Cap", "Sunscreen"])
    elif weather == "cold":
        generated.setdefault("Weather Gear", []).extend(["Gloves", "Thermal Wear"])

    return generated

# --------------------------------------------------
# ROUTES
# --------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (email, username, password_hash) VALUES (?, ?, ?)",
                (
                    request.form['email'].lower(),
                    request.form['username'],
                    generate_password_hash(request.form['password'])
                )
            )
            db.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email already registered.", "danger")
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE email=?",
            (request.form['email'].lower(),)
        ).fetchone()
        if user and check_password_hash(user['password_hash'], request.form['password']):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        flash("Invalid credentials.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM packing_lists WHERE user_id=? ORDER BY created_at DESC",
        (session['user_id'],)
    ).fetchall()

    trips = [{
        "id": r["id"],
        "destination": r["destination"],
        "duration": r["duration"],
        "activities": r["activities"].split(",") if r["activities"] else [],
        "items": json.loads(r["items"]),
        "created_at": r["created_at"]
    } for r in rows]

    return render_template(
        "dashboard.html",
        trips=trips,
        trips_json=json.dumps(trips),
        username=session['username']
    )

@app.route('/create-list', methods=['GET','POST'])
@login_required
def create_list():
    if request.method == 'POST':
        items = generate_packing_list(
            request.form['destination'],
            request.form['duration'],
            request.form.getlist('activities')
        )

        db = get_db()
        db.execute(
            """INSERT INTO packing_lists
               (user_id, destination, duration, activities, items)
               VALUES (?, ?, ?, ?, ?)""",
            (
                session['user_id'],
                request.form['destination'],
                request.form['duration'],
                ",".join(request.form.getlist('activities')),
                json.dumps(items)
            )
        )
        db.commit()
        return redirect(url_for('packing_result'))

    return render_template('create_list.html')

# --------------------------------------------------
# API: ACTIVITIES (POST – FIXED)
# --------------------------------------------------
@app.route('/api/activities', methods=['POST'])
@login_required
def api_activities():
    data = request.get_json()
    destination = data.get("destination", "")
    return jsonify({
        "activities": get_activities_for_destination(destination)
    })

# --------------------------------------------------
# API: UPDATE LIST
# --------------------------------------------------
@app.route('/api/update-list', methods=['POST'])
@login_required
def api_update_list():
    data = request.get_json()
    db = get_db()
    db.execute(
        "UPDATE packing_lists SET items=? WHERE id=? AND user_id=?",
        (json.dumps(data["items"]), data["id"], session['user_id'])
    )
    db.commit()
    return jsonify({"success": True})

# --------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
