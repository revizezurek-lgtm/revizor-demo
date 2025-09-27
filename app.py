from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import sqlite3, os, hashlib
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "database.db")
UPLOAD_DIR = os.path.join(APP_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = "change-me-please"  # demo účely

def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = get_db()
    cur = con.cursor()
    cur.executescript("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT, email TEXT UNIQUE, password_hash TEXT,
    logo_path TEXT, stamp_path TEXT
);
CREATE TABLE IF NOT EXISTS customers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT, ico TEXT, address TEXT, contact TEXT
);
CREATE TABLE IF NOT EXISTS inspections(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER, customer_id INTEGER,
    number TEXT, type TEXT, place TEXT,
    date TEXT, next_date TEXT, description TEXT
);
CREATE TABLE IF NOT EXISTS panels(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inspection_id INTEGER, name TEXT, maker TEXT, serial TEXT
);
CREATE TABLE IF NOT EXISTS outlets(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    panel_id INTEGER,
    code TEXT, descr TEXT, cable TEXT, cross_section TEXT,
    breaker TEXT, zs TEXT, rcd_time TEXT, insulation TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS standards(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT, edition TEXT, article TEXT, note TEXT, status TEXT
);
CREATE TABLE IF NOT EXISTS inspection_standards(
    inspection_id INTEGER, standard_id INTEGER,
    PRIMARY KEY (inspection_id, standard_id)
);
""")
    con.commit()
    con.close()

@app.before_request
def ensure_db():
    if not os.path.exists(DB_PATH):
        init_db()

def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*a, **kw):
        if "uid" not in session:
            return redirect(url_for("login"))
        return fn(*a, **kw)
    return wrapper

@app.route("/")
def index():
    if "uid" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        pw = request.form["password"]
        con = get_db()
        try:
            con.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                        (name,email,hash_pw(pw)))
            con.commit()
            flash("Účet vytvořen, přihlas se.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("E-mail už existuje.")
        finally:
            con.close()
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        pw = request.form["password"]
        con = get_db()
        row = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        con.close()
        if row and row["password_hash"] == hash_pw(pw):
            session["uid"] = row["id"]
            session["uname"] = row["name"]
            return redirect(url_for("dashboard"))
        flash("Neplatné přihlašovací údaje.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    con = get_db()
    cust_count = con.execute("SELECT COUNT(*) FROM customers WHERE user_id=?", (session["uid"],)).fetchone()[0]
    insp_count = con.execute("SELECT COUNT(*) FROM inspections WHERE user_id=?", (session["uid"],)).fetchone()[0]
    con.close()
    return render_template("dashboard.html", cust_count=cust_count, insp_count=insp_count)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
