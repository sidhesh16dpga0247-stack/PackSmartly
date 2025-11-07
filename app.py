import json
# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, 'app.db')

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret-change-me')  # set real secret in production

# --- Database helper ---
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

# --- Login required decorator ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def get_weather(destination):
    """
    Simple offline weather heuristics. This does NOT call an external API.
    You can expand the city lists as needed for your IA.
    """
    if not destination:
        return "normal"

    dest = destination.strip().lower()
    tropical = {"goa", "bali", "maldives", "bangkok", "phuket"}
    cold = {"london", "toronto", "reykjavik", "oslo", "moscow"}

    # check simple containment
    for t in tropical:
        if t in dest:
            return "hot"
    for c in cold:
        if c in dest:
            return "cold"
    return "normal"

def generate_packing_list(destination, duration, activities):
    base_items = {
        "Essentials": ["Phone", "Charger", "Wallet", "Passport", "Travel Tickets"],
        "Clothing": ["Underwear", "Socks", "T-Shirts", "Pants", "Jacket"],
        "Toiletries": ["Toothbrush", "Toothpaste", "Deodorant", "Soap"],
    }

    activity_items = {
        "Swimming": ["Swimsuit", "Towel", "Flip-flops", "Waterproof Bag"],
        "Hiking": ["Hiking Shoes", "Water Bottle", "Backpack", "Trail Snacks", "Rain Jacket"],
        "Business": ["Formal Shirt", "Laptop", "Notebook", "Business Shoes", "Blazer"],
        "Gym": ["Gym Clothes", "Shoes", "Protein Shaker", "Towel"],
        "Photography": ["Camera", "Extra Batteries", "SD Cards", "Tripod"],
        "Road Trip": ["Neck Pillow", "Snacks", "Sunglasses", "Car Charger"],
        "Camping": ["Tent", "Sleeping Bag", "Flashlight", "Portable Stove"],
        "Adventure Sports": ["Gloves", "Helmet", "Sportswear", "Energy Bars"],
        "Sightseeing": ["Cap", "Sunscreen", "Comfortable Shoes", "Water Bottle"],
        "Beach Day": ["Beach Towel", "Sunscreen", "Sandals", "Beach Bag"],
        "Shopping": ["Reusable Bags", "Comfortable Shoes", "Wallet"],
        "Nightlife": ["Smart Casual Clothes", "Perfume", "ID Card"],
        "Museum Tour": ["Notebook", "Comfortable Shoes"],
        "Running": ["Running Shoes", "Sportswear", "Sweatband"],
        "Festival/Concert": ["Earplugs", "Portable Fan", "Power Bank"],
        "Cycling": ["Cycling Shorts", "Helmet", "Water Bottle"]
    }


    # Start with a shallow copy of base items (we will mutate lists)
    generated_list = {k: list(v) for k, v in base_items.items()}

    # Add items based on activities
    for activity in activities:
        if activity in activity_items:
            generated_list.setdefault("Activity Gear", [])
            generated_list["Activity Gear"].extend(activity_items[activity])

    # Add items based on number of days (simple rule)
    try:
        days = int(duration)
        if days < 1:
            days = 1
    except Exception:
        days = 1

    generated_list["Clothing"].append(f"{days} pairs of socks")
    generated_list["Clothing"].append(f"{days} sets of underwear")

    # WEATHER-BASED RECOMMENDATIONS (simple offline logic)
    weather = get_weather(destination)
    if weather == "hot":
        generated_list.setdefault("Weather Gear", []).extend(["Sunscreen", "Cap", "Reusable Water Bottle"])
    elif weather == "cold":
        generated_list.setdefault("Weather Gear", []).extend(["Gloves", "Scarf", "Thermal Layer"])

    return generated_list

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        confirm = request.form.get('confirm','')

        # basic validation
        if not username or not email or not password:
            flash("Please fill all required fields.", "danger")
            return render_template('register.html', username=username, email=email)

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template('register.html', username=username, email=email)

        db = get_db()
        try:
            password_hash = generate_password_hash(password)
            db.execute("INSERT INTO users (email, username, password_hash) VALUES (?, ?, ?)",
                       (email, username, password_hash))
            db.commit()
            flash("Account created. Please log in.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("An account with that email already exists.", "danger")
            return render_template('register.html', username=username, email=email)

    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            # login success
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f"Welcome back, {user['username']}!", "success")
            next_page = request.args.get('next') or url_for('dashboard')
            return redirect(next_page)
        else:
            flash("Invalid email or password.", "danger")
            return render_template('login.html', email=email)

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    rows = db.execute("""
        SELECT id, destination, duration, activities, items, created_at
        FROM packing_lists
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (session['user_id'],)).fetchall()

    # Convert rows to Python dictionaries; parse JSON 'items' field
    trips = []
    for r in rows:
        try:
            items = json.loads(r['items'])
        except Exception:
            items = {}
        activities = (r['activities'] or "").split(",") if r['activities'] else []
        trips.append({
            "id": r["id"],  # id is kept server-side; it will be embedded in JS data (not in any URL)
            "destination": r["destination"],
            "duration": r["duration"],
            "activities": activities,
            "items": items,
            "created_at": r["created_at"]
        })

    # Pass trips as JSON to the template so client-side JS can manage editing/download without id in URL
    trips_json = json.dumps(trips, default=str)  # default=str for datetime serialization safety

    return render_template('dashboard.html', username=session['username'], trips=trips, trips_json=trips_json)

@app.route('/create-list', methods=['GET', 'POST'])
@login_required
def create_list():
    if request.method == 'POST':
        destination = request.form.get('destination')
        duration = request.form.get('duration') or "1"
        activities = request.form.getlist('activities')

        packing_items = generate_packing_list(destination, duration, activities)

        db = get_db()
        db.execute("""
            INSERT INTO packing_lists (user_id, destination, duration, activities, items)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session['user_id'],
            destination,
            duration,
            ",".join(activities),
            json.dumps(packing_items)
        ))
        db.commit()

        return redirect(url_for('dashboard'))

    return render_template('create_list.html')

# --- API endpoint: update a saved list (receives JSON payload, no id in URL) ---
@app.route('/api/update-list', methods=['POST'])
@login_required
def api_update_list():
    """
    Expected JSON payload:
    {
        "id": <integer>,
        "items": { "Category": ["item1", "item2", ...], ... },
        "destination": "New Destination (optional)",
        "duration": 3 (optional),
        "activities": ["Swimming","Hiking"] (optional)
    }
    The id is supplied in the JSON body by client JS (not the URL).
    """
    payload = request.get_json(force=True, silent=True)
    if not payload:
        return jsonify({"success": False, "error": "Invalid JSON"}), 400

    list_id = payload.get("id")
    items = payload.get("items")
    destination = payload.get("destination")
    duration = payload.get("duration")
    activities = payload.get("activities")

    if not list_id or not items:
        return jsonify({"success": False, "error": "Missing id or items"}), 400

    db = get_db()
    # Verify ownership before updating
    row = db.execute("SELECT user_id FROM packing_lists WHERE id = ?", (list_id,)).fetchone()
    if not row or row["user_id"] != session['user_id']:
        return jsonify({"success": False, "error": "Not found or unauthorized"}), 403

    # Prepare fields to update
    fields = []
    params = []

    # items (JSON)
    fields.append("items = ?")
    params.append(json.dumps(items))

    # optional fields
    if destination is not None:
        fields.append("destination = ?")
        params.append(destination)
    if duration is not None:
        fields.append("duration = ?")
        params.append(duration)
    if activities is not None:
        if isinstance(activities, list):
            activities_db = ",".join(activities)
        else:
            activities_db = str(activities)
        fields.append("activities = ?")
        params.append(activities_db)

    params.append(list_id)

    sql = f"UPDATE packing_lists SET {', '.join(fields)} WHERE id = ?"
    db.execute(sql, tuple(params))
    db.commit()

    return jsonify({"success": True})

# NOTE: The route view-list/<int:list_id> has been intentionally removed.
# Client-side JavaScript will use the embedded TRIPS_DATA to display and edit lists,
# and will call /api/update-list to save changes. This keeps ids out of visible URLs.

# Run
if __name__ == '__main__':
    app.run(debug=True)
