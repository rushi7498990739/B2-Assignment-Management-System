from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import sqlite3, os
from functools import wraps

app = Flask(__name__)
app.secret_key = "b2-assignment-system-secret"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "txt", "zip", "png", "jpg", "jpeg"}

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','student'))
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS assignments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            subject TEXT NOT NULL,
            due_date TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS submissions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            answer TEXT,
            filename TEXT,
            submitted_at TEXT NOT NULL,
            UNIQUE(assignment_id, student_id)
        )""")
        if not con.execute("SELECT id FROM users WHERE email=?", ("admin@demo.com",)).fetchone():
            con.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
                        ("Demo Professor","admin@demo.com",generate_password_hash("admin123"),"admin"))
        if not con.execute("SELECT id FROM users WHERE email=?", ("student@demo.com",)).fetchone():
            con.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
                        ("Demo Student","student@demo.com",generate_password_hash("student123"),"student"))

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login_choice"))
        return f(*args, **kwargs)
    return wrapper

def role_required(role):
    def deco(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get("role") != role:
                flash("You do not have permission to access this page.", "error")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return wrapper
    return deco

@app.route("/")
def home():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login_choice"))

@app.route("/login")
def login_choice():
    return render_template("login_choice.html")

@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        with db() as con:
            user = con.execute("SELECT * FROM users WHERE email=? AND role='admin'", (email,)).fetchone()
        if user and check_password_hash(user["password"], password):
            session.clear()
            session.update(user_id=user["id"], name=user["name"], role="admin")
            return redirect(url_for("dashboard"))
        flash("Invalid professor/admin login.", "error")
    return render_template("admin_login.html")

@app.route("/student/login", methods=["GET","POST"])
def student_login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        with db() as con:
            user = con.execute("SELECT * FROM users WHERE email=? AND role='student'", (email,)).fetchone()
        if user and check_password_hash(user["password"], password):
            session.clear()
            session.update(user_id=user["id"], name=user["name"], role="student")
            return redirect(url_for("dashboard"))
        flash("Invalid student login.", "error")
    return render_template("student_login.html")

@app.route("/admin/register", methods=["GET","POST"])
def admin_register():
    if request.method == "POST":
        name=request.form["name"].strip()
        email=request.form["email"].strip().lower()
        password=request.form["password"]
        if len(password) < 6:
            flash("Password must contain at least 6 characters.", "error")
            return render_template("admin_register.html")
        try:
            with db() as con:
                con.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
                            (name,email,generate_password_hash(password),"admin"))
            flash("Admin/professor account created. Please login.", "success")
            return redirect(url_for("admin_login"))
        except sqlite3.IntegrityError:
            flash("Email already registered.", "error")
    return render_template("admin_register.html")

@app.route("/student/register", methods=["GET","POST"])
def student_register():
    if request.method == "POST":
        name=request.form["name"].strip()
        email=request.form["email"].strip().lower()
        password=request.form["password"]
        if len(password) < 6:
            flash("Password must contain at least 6 characters.", "error")
            return render_template("student_register.html")
        try:
            with db() as con:
                con.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
                            (name,email,generate_password_hash(password),"student"))
            flash("Student account created. Please login.", "success")
            return redirect(url_for("student_login"))
        except sqlite3.IntegrityError:
            flash("Email already registered.", "error")
    return render_template("student_register.html")

@app.route("/logout")
def logout():
    session.clear()
    return render_template("login_choice.html")

@app.route("/dashboard")
@login_required
def dashboard():
    with db() as con:
        assignments=con.execute("""
            SELECT a.*, u.name AS professor,
            (SELECT id FROM submissions s WHERE s.assignment_id=a.id AND s.student_id=?) AS submission_id
            FROM assignments a JOIN users u ON u.id=a.created_by
            ORDER BY a.due_date ASC, a.id DESC
        """,(session["user_id"],)).fetchall()
    return render_template("dashboard.html", assignments=assignments)

@app.route("/admin/assignments/new", methods=["GET","POST"])
@login_required
@role_required("admin")
def create_assignment():
    if request.method=="POST":
        title=request.form["title"].strip()
        description=request.form["description"].strip()
        subject=request.form["subject"].strip()
        due_date=request.form["due_date"]
        if not all([title,description,subject,due_date]):
            flash("Please fill all fields.", "error")
            return render_template("create_assignment.html")
        with db() as con:
            con.execute("""INSERT INTO assignments(title,description,subject,due_date,created_by,created_at)
                           VALUES(?,?,?,?,?,?)""",
                        (title,description,subject,due_date,session["user_id"],
                         datetime.now().strftime("%Y-%m-%d %H:%M")))
        flash("Assignment posted successfully.", "success")
        return redirect(url_for("dashboard"))
    return render_template("create_assignment.html")

@app.route("/student/submit/<int:assignment_id>", methods=["GET","POST"])
@login_required
@role_required("student")
def submit_assignment(assignment_id):
    with db() as con:
        assignment=con.execute("SELECT * FROM assignments WHERE id=?", (assignment_id,)).fetchone()
        old=con.execute("SELECT * FROM submissions WHERE assignment_id=? AND student_id=?",
                        (assignment_id,session["user_id"])).fetchone()
    if not assignment:
        flash("Assignment not found.", "error")
        return redirect(url_for("dashboard"))
    if request.method=="POST":
        answer=request.form.get("answer","").strip()
        file=request.files.get("file")
        filename=old["filename"] if old else None
        if file and file.filename:
            safe=secure_filename(file.filename)
            ext=safe.rsplit(".",1)[-1].lower() if "." in safe else ""
            if ext not in ALLOWED_EXTENSIONS:
                flash("Allowed: PDF, DOC, DOCX, TXT, ZIP, PNG, JPG, JPEG.", "error")
                return render_template("submit_assignment.html",assignment=assignment,old=old)
            filename=f"{session['user_id']}_{assignment_id}_{safe}"
            file.save(os.path.join(UPLOAD_DIR,filename))
        if not answer and not filename:
            flash("Please enter an answer or upload a file.", "error")
            return render_template("submit_assignment.html",assignment=assignment,old=old)
        with db() as con:
            if old:
                con.execute("""UPDATE submissions SET answer=?,filename=?,submitted_at=? WHERE id=?""",
                            (answer,filename,datetime.now().strftime("%Y-%m-%d %H:%M"),old["id"]))
            else:
                con.execute("""INSERT INTO submissions(assignment_id,student_id,answer,filename,submitted_at)
                               VALUES(?,?,?,?,?)""",
                            (assignment_id,session["user_id"],answer,filename,
                             datetime.now().strftime("%Y-%m-%d %H:%M")))
        flash("Assignment submitted successfully.", "success")
        return redirect(url_for("dashboard"))
    return render_template("submit_assignment.html",assignment=assignment,old=old)

@app.route("/admin/submissions/<int:assignment_id>")
@login_required
@role_required("admin")
def submissions(assignment_id):
    with db() as con:
        assignment=con.execute("SELECT * FROM assignments WHERE id=?", (assignment_id,)).fetchone()
        rows=con.execute("""SELECT s.*,u.name,u.email FROM submissions s
                            JOIN users u ON u.id=s.student_id
                            WHERE s.assignment_id=? ORDER BY s.submitted_at DESC""",(assignment_id,)).fetchall()
    return render_template("submissions.html",assignment=assignment,submissions=rows)

@app.route("/download/<path:filename>")
@login_required
@role_required("admin")
def download(filename):
    return send_from_directory(UPLOAD_DIR,filename,as_attachment=True)

if __name__=="__main__":
    init_db()
    app.run(debug=True)
