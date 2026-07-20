"""Clean Community – Sanitation & Hygiene Portal.

Run this file after installing requirements to start the Flask development server.
The SQLite database and uploads folder are created automatically on first run.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "database.db"
UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
ISSUE_TYPES = (
    "Garbage Overflow",
    "Open Drainage",
    "Dirty Public Toilet",
    "Water Stagnation",
    "Drinking Water Issue",
    "Waste Dumping",
    "Others",
)
STATUSES = ("Pending", "In Progress", "Resolved")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "change-this-demo-secret-before-deploying"),
    UPLOAD_FOLDER=str(UPLOAD_FOLDER),
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,  # Keep uploads manageable for this portal.
)


def get_db() -> sqlite3.Connection:
    """Open one SQLite connection per request and return rows as dictionaries."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error: Exception | None = None) -> None:
    """Close the request database connection when Flask finishes the request."""
    database = g.pop("db", None)
    if database is not None:
        database.close()


def init_db() -> None:
    """Create the application tables on a clean first run."""
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            village TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            issue_type TEXT NOT NULL,
            location TEXT NOT NULL,
            village TEXT NOT NULL,
            description TEXT NOT NULL,
            image TEXT,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
        """
    )
    db.commit()


def allowed_file(filename: str) -> bool:
    """Return True only for the image formats accepted by the complaint form."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def current_user() -> sqlite3.Row | None:
    """Fetch the signed-in resident for templates and protected pages."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


@app.context_processor
def inject_global_data() -> dict:
    """Make the current resident and current year available to every template."""
    return {"current_user": current_user(), "current_year": datetime.now().year}


def login_required(view):
    """Require a resident session for user-only features."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    """Require the separate administrator session for the admin area."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Please log in as an administrator to continue.", "error")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped_view


@app.errorhandler(413)
def upload_too_large(_error):
    flash("Photo is too large. Please choose an image smaller than 5 MB.", "error")
    return redirect(request.referrer or url_for("report_issue"))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        mobile = request.form.get("mobile", "").strip()
        village = request.form.get("village", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not all((full_name, mobile, village, email, password, confirm_password)):
            flash("Please fill in every field.", "error")
        elif "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            flash("Please enter a valid email address.", "error")
        elif len(mobile) < 10 or not mobile.replace("+", "").replace(" ", "").replace("-", "").isdigit():
            flash("Please enter a valid mobile number.", "error")
        elif len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
        elif password != confirm_password:
            flash("The passwords do not match.", "error")
        elif get_db().execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
            flash("An account with this email already exists. Please log in.", "error")
        else:
            db = get_db()
            db.execute(
                """INSERT INTO users (full_name, mobile, village, email, password_hash)
                   VALUES (?, ?, ?, ?, ?)""",
                (full_name, mobile, village, email, generate_password_hash(password)),
            )
            db.commit()
            flash("Your account has been created. Please log in.", "success")
            return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            flash(f"Welcome back, {user['full_name'].split()[0]}!", "success")
            return redirect(url_for("dashboard"))
        flash("Email or password is not correct. Please try again.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out safely.", "success")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    user_id = session["user_id"]
    stats = db.execute(
        """SELECT COUNT(*) AS total,
                  SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending,
                  SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) AS resolved
           FROM complaints WHERE user_id = ?""",
        (user_id,),
    ).fetchone()
    return render_template("dashboard.html", stats=stats)


@app.route("/report", methods=["GET", "POST"])
@login_required
def report_issue():
    user = current_user()
    if request.method == "POST":
        location = request.form.get("location", "").strip()
        issue_type = request.form.get("issue_type", "").strip()
        description = request.form.get("description", "").strip()
        image = request.files.get("image")

        if not all((location, issue_type, description)):
            flash("Please complete the location, issue type, and description.", "error")
        elif issue_type not in ISSUE_TYPES:
            flash("Please choose an issue type from the list.", "error")
        elif image and image.filename and not allowed_file(image.filename):
            flash("Please upload a PNG, JPG, JPEG, GIF, or WEBP image only.", "error")
        else:
            image_name = None
            if image and image.filename:
                safe_name = secure_filename(image.filename)
                extension = safe_name.rsplit(".", 1)[1].lower()
                image_name = f"{uuid.uuid4().hex}.{extension}"
                image.save(UPLOAD_FOLDER / image_name)

            db = get_db()
            db.execute(
                """INSERT INTO complaints
                   (user_id, issue_type, location, village, description, image, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?)""",
                (
                    user["id"], issue_type, location, user["village"], description, image_name,
                    datetime.now().strftime("%d %b %Y, %I:%M %p"),
                ),
            )
            db.commit()
            flash("Your complaint has been submitted. Thank you for helping keep the village clean!", "success")
            return redirect(url_for("my_complaints"))

    return render_template("report_issue.html", issue_types=ISSUE_TYPES, user=user)


@app.route("/complaints")
@login_required
def my_complaints():
    complaints = get_db().execute(
        "SELECT * FROM complaints WHERE user_id = ? ORDER BY id DESC", (session["user_id"],)
    ).fetchall()
    return render_template("my_complaints.html", complaints=complaints)


@app.route("/awareness")
@login_required
def awareness():
    return render_template("awareness.html")


@app.route("/emergency")
@login_required
def emergency():
    return render_template("emergency.html")


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        mobile = request.form.get("mobile", "").strip()
        village = request.form.get("village", "").strip()
        email = request.form.get("email", "").strip().lower()

        existing = get_db().execute(
            "SELECT id FROM users WHERE email = ? AND id != ?", (email, user["id"])
        ).fetchone()
        if not all((full_name, mobile, village, email)):
            flash("Please fill in every field.", "error")
        elif "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            flash("Please enter a valid email address.", "error")
        elif len(mobile) < 10:
            flash("Please enter a valid mobile number.", "error")
        elif existing:
            flash("This email address is already used by another account.", "error")
        else:
            db = get_db()
            db.execute(
                "UPDATE users SET full_name = ?, mobile = ?, village = ?, email = ? WHERE id = ?",
                (full_name, mobile, village, email, user["id"]),
            )
            db.commit()
            flash("Your profile has been updated.", "success")
            return redirect(url_for("profile"))

    return render_template("profile.html", user=current_user())


def admin_credentials_are_valid(email: str, password: str) -> bool:
    """Check environment-configurable credentials for the prototype admin account."""
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@cleancommunity.local").lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    return email.lower() == admin_email and password == admin_password


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("is_admin"):
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if admin_credentials_are_valid(email, password):
            session.clear()
            session["is_admin"] = True
            flash("Administrator login successful.", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Administrator email or password is not correct.", "error")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("Administrator has been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    stats = db.execute(
        """SELECT
             (SELECT COUNT(*) FROM users) AS users,
             (SELECT COUNT(*) FROM complaints) AS complaints,
             (SELECT COUNT(*) FROM complaints WHERE status = 'Pending') AS pending,
             (SELECT COUNT(*) FROM complaints WHERE status = 'Resolved') AS resolved"""
    ).fetchone()
    recent_complaints = db.execute(
        """SELECT complaints.*, users.full_name
           FROM complaints JOIN users ON complaints.user_id = users.id
           ORDER BY complaints.id DESC LIMIT 5"""
    ).fetchall()
    return render_template("admin_dashboard.html", stats=stats, recent_complaints=recent_complaints)


@app.route("/admin/complaints")
@admin_required
def admin_complaints():
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    query = """SELECT complaints.*, users.full_name, users.mobile
               FROM complaints JOIN users ON complaints.user_id = users.id WHERE 1 = 1"""
    values: list[str] = []
    if search:
        query += " AND (complaints.id LIKE ? OR complaints.issue_type LIKE ? OR complaints.location LIKE ? OR users.full_name LIKE ?)"
        term = f"%{search}%"
        values.extend((term, term, term, term))
    if status in STATUSES:
        query += " AND complaints.status = ?"
        values.append(status)
    query += " ORDER BY complaints.id DESC"
    complaints = get_db().execute(query, values).fetchall()
    return render_template(
        "admin_complaints.html", complaints=complaints, statuses=STATUSES, search=search, selected_status=status
    )


@app.route("/admin/complaints/<int:complaint_id>/status", methods=["POST"])
@admin_required
def update_complaint_status(complaint_id: int):
    status = request.form.get("status", "")
    if status not in STATUSES:
        flash("Please choose a valid complaint status.", "error")
    else:
        get_db().execute("UPDATE complaints SET status = ? WHERE id = ?", (status, complaint_id))
        get_db().commit()
        flash(f"Complaint #{complaint_id} status updated to {status}.", "success")
    return redirect(url_for("admin_complaints", **request.args))


@app.route("/admin/complaints/<int:complaint_id>/delete", methods=["POST"])
@admin_required
def delete_complaint(complaint_id: int):
    db = get_db()
    complaint = db.execute("SELECT image FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    if not complaint:
        abort(404)
    # Remove the associated stored image too, when one was uploaded.
    if complaint["image"]:
        image_path = UPLOAD_FOLDER / complaint["image"]
        if image_path.is_file():
            image_path.unlink()
    db.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))
    db.commit()
    flash(f"Complaint #{complaint_id} has been deleted.", "success")
    return redirect(url_for("admin_complaints"))


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)
