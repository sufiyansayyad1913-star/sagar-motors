from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from datetime import datetime
import os
from functools import wraps

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "temporary-local-secret-key"
)

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "sagar123")

DATABASE = "database.db"


# ---------------- DATABASE CONNECTION ----------------

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))

        flash("Invalid username or password", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- CREATE TABLE ----------------

def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_number TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            mobile TEXT,
            vehicle_model TEXT,
            km INTEGER,
            problem TEXT,
            work_done TEXT,
            mechanic TEXT,
            status TEXT DEFAULT 'Pending',
            amount REAL DEFAULT 0,
            remarks TEXT,
            date TEXT NOT NULL,
            time_in TEXT NOT NULL,
            time_out TEXT
        )
    """)

    conn.commit()
    conn.close()


# ---------------- DASHBOARD ----------------
@app.route("/")
@login_required
def dashboard():

    conn = get_db_connection()

    today = datetime.now().strftime("%Y-%m-%d")

    total_today = conn.execute(
        "SELECT COUNT(*) FROM vehicles WHERE date = ?",
        (today,)
    ).fetchone()[0]

    pending = conn.execute(
        "SELECT COUNT(*) FROM vehicles WHERE status = 'Pending'"
    ).fetchone()[0]

    in_progress = conn.execute(
        "SELECT COUNT(*) FROM vehicles WHERE status = 'In Progress'"
    ).fetchone()[0]

    completed = conn.execute(
        "SELECT COUNT(*) FROM vehicles WHERE status = 'Completed'"
    ).fetchone()[0]

    collection = conn.execute(
        "SELECT SUM(amount) FROM vehicles WHERE date = ? AND status = 'Completed'",
        (today,)
    ).fetchone()[0]

    collection = collection if collection else 0

    recent = conn.execute("""
        SELECT *
        FROM vehicles
        ORDER BY id DESC
        LIMIT 10
    """).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        total_today=total_today,
        pending=pending,
        in_progress=in_progress,
        completed=completed,
        collection=collection,
        recent=recent
    )


# ---------------- ADD VEHICLE ----------------

@app.route("/add", methods=["GET", "POST"])
@login_required
def add_vehicle():

    if request.method == "POST":

        vehicle_number = request.form["vehicle_number"].upper()
        customer_name = request.form["customer_name"]
        mobile = request.form["mobile"]
        vehicle_model = request.form["vehicle_model"]
        km = request.form["km"]
        problem = request.form["problem"]
        work_done = request.form["work_done"]
        mechanic = request.form["mechanic"]
        status = request.form["status"]
        amount = request.form["amount"]
        remarks = request.form["remarks"]

        now = datetime.now()

        date = now.strftime("%Y-%m-%d")
        time_in = now.strftime("%I:%M %p")

        conn = get_db_connection()

        conn.execute("""
            INSERT INTO vehicles
            (
                vehicle_number,
                customer_name,
                mobile,
                vehicle_model,
                km,
                problem,
                work_done,
                mechanic,
                status,
                amount,
                remarks,
                date,
                time_in
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vehicle_number,
            customer_name,
            mobile,
            vehicle_model,
            km,
            problem,
            work_done,
            mechanic,
            status,
            amount,
            remarks,
            date,
            time_in
        ))

        conn.commit()
        conn.close()

        flash("Vehicle record added successfully!", "success")

        return redirect(url_for("dashboard"))

    return render_template("add_vehicle.html")


# ---------------- ALL VEHICLES ----------------
@app.route("/vehicles")
@login_required
def vehicles():

    search = request.args.get("search", "")

    conn = get_db_connection()

    if search:

        vehicles = conn.execute("""
            SELECT *
            FROM vehicles
            WHERE vehicle_number LIKE ?
               OR customer_name LIKE ?
               OR mobile LIKE ?
            ORDER BY id DESC
        """, (
            f"%{search.upper()}%",
            f"%{search}%",
            f"%{search}%"
        )).fetchall()

    else:

        vehicles = conn.execute("""
            SELECT *
            FROM vehicles
            ORDER BY id DESC
        """).fetchall()

    conn.close()

    return render_template(
        "vehicles.html",
        vehicles=vehicles,
        search=search
    )


# ---------------- VEHICLE HISTORY ----------------

@app.route("/history/<vehicle_number>")
@login_required
def history(vehicle_number):

    conn = get_db_connection()

    records = conn.execute("""
        SELECT *
        FROM vehicles
        WHERE vehicle_number = ?
        ORDER BY id DESC
    """, (vehicle_number.upper(),)).fetchall()

    conn.close()

    return render_template(
        "history.html",
        records=records,
        vehicle_number=vehicle_number.upper()
    )


# ---------------- EDIT ----------------

@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_vehicle(id):

    conn = get_db_connection()

    vehicle = conn.execute(
        "SELECT * FROM vehicles WHERE id = ?",
        (id,)
    ).fetchone()

    if not vehicle:
        conn.close()
        return "Vehicle record not found", 404

    if request.method == "POST":

        vehicle_number = request.form["vehicle_number"].upper()
        customer_name = request.form["customer_name"]
        mobile = request.form["mobile"]
        vehicle_model = request.form["vehicle_model"]
        km = request.form["km"]
        problem = request.form["problem"]
        work_done = request.form["work_done"]
        mechanic = request.form["mechanic"]
        status = request.form["status"]
        amount = request.form["amount"]
        remarks = request.form["remarks"]
        time_out = request.form["time_out"]

        conn.execute("""
            UPDATE vehicles
            SET
                vehicle_number = ?,
                customer_name = ?,
                mobile = ?,
                vehicle_model = ?,
                km = ?,
                problem = ?,
                work_done = ?,
                mechanic = ?,
                status = ?,
                amount = ?,
                remarks = ?,
                time_out = ?
            WHERE id = ?
        """, (
            vehicle_number,
            customer_name,
            mobile,
            vehicle_model,
            km,
            problem,
            work_done,
            mechanic,
            status,
            amount,
            remarks,
            time_out,
            id
        ))

        conn.commit()
        conn.close()

        flash("Vehicle record updated successfully!", "success")

        return redirect(url_for("vehicles"))

    conn.close()

    return render_template(
        "edit_vehicle.html",
        vehicle=vehicle
    )


# ---------------- DELETE ----------------

@app.route("/delete/<int:id>")
@login_required
def delete_vehicle(id):

    conn = get_db_connection()

    conn.execute(
        "DELETE FROM vehicles WHERE id = ?",
        (id,)
    )

    conn.commit()
    conn.close()

    flash("Vehicle record deleted!", "success")

    return redirect(url_for("vehicles"))


# ---------------- RUN APP ----------------

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )