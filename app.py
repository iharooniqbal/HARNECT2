"""
Clean single-file Flask app for HARNECT using SQLite persistence.
Features:
 - Signup / Login (passwords hashed)
 - Guest login
 - Upload posts & stories (files saved to static/uploads)
 - Profile edit (username, bio, profile pic)
 - Like/unlike posts, comment on posts
 - Follow/unfollow users
 - Feedback
 - Simple search/explore
 - DB initialization on startup (creates tables if missing)

Notes:
 - Set HARNECT_SECRET_KEY in env for persistent sessions.
 - Configure HARNECT_MAX_UPLOAD_MB to change max upload size (default 50 MB).
 - In production: run behind a WSGI server, enable SESSION_COOKIE_SECURE, serve uploads safely.

"""

import os
import uuid
import random
import sqlite3
from functools import wraps
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, flash, abort, g, send_from_directory
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

# -------------------------
# Configuration
# -------------------------
BASE_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "mp4", "webm", "ogg", "avi"}
ALLOWED_MIMETYPE_PREFIX = ("image/", "video/")

DATABASE_PATH = os.environ.get("HARNECT_DB_PATH") or os.path.join(BASE_DIR, "harnect.db")

app = Flask(__name__)
app.secret_key = os.environ.get("HARNECT_SECRET_KEY") or os.urandom(24)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("HARNECT_MAX_UPLOAD_MB", 50)) * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
# app.config["SESSION_COOKIE_SECURE"] = True  # enable in production with HTTPS

# -------------------------
# Database helpers
# -------------------------

def get_db():
    db = getattr(g, "db", None)
    if db is None:
        db = g.db = sqlite3.connect(DATABASE_PATH)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_db(e=None):
    db = getattr(g, "db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE_PATH)
    c = db.cursor()
    # users, posts, stories, followers, likes, comments, feedback
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT,
        bio TEXT DEFAULT '',
        profile_pic TEXT DEFAULT 'user.png',
        email TEXT,
        guest INTEGER DEFAULT 0,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        filename TEXT,
        caption TEXT,
        type TEXT DEFAULT 'post',
        created_at TEXT,
        FOREIGN KEY(username) REFERENCES users(username)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS followers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        follower TEXT,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        username TEXT,
        created_at TEXT,
        FOREIGN KEY(post_id) REFERENCES posts(id)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        username TEXT,
        text TEXT,
        created_at TEXT,
        FOREIGN KEY(post_id) REFERENCES posts(id)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        message TEXT,
        created_at TEXT
    )
    """)

    db.commit()
    db.close()


# Initialize DB on startup if missing
if not os.path.exists(DATABASE_PATH):
    init_db()


# -------------------------
# Helpers
# -------------------------

def allowed_file(filename: str) -> bool:
    return (
        isinstance(filename, str)
        and "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def safe_save_file(storage_file, target_folder=None):
    if target_folder is None:
        target_folder = app.config["UPLOAD_FOLDER"]
    filename = secure_filename(storage_file.filename)
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    new_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    dest = os.path.join(target_folder, new_name)
    storage_file.save(dest)
    return new_name


def validate_uploaded_file(storage_file):
    if not storage_file or storage_file.filename.strip() == "":
        return False, "No file uploaded."

    if not allowed_file(storage_file.filename):
        return False, "File extension not allowed."

    mimetype = (storage_file.mimetype or "").lower()
    if not any(mimetype.startswith(pref) for pref in ALLOWED_MIMETYPE_PREFIX):
        return False, f"Unexpected file type: {mimetype}."

    return True, "OK"


def login_required(route_func):
    @wraps(route_func)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return route_func(*args, **kwargs)
    return wrapped


def user_exists(username):
    db = get_db()
    r = db.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
    return bool(r)


# -------------------------
# Routes
# -------------------------
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/")
def splash():
    return render_template("splash.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        e = request.form.get("email", "").strip() or None
        p = request.form.get("password", "")
        if not u or not p:
            return render_template("signup.html", error="Username and password required")
        if user_exists(u):
            return render_template("signup.html", error="Username already exists")
        pw_hash = generate_password_hash(p)
        db = get_db()
        db.execute(
            "INSERT INTO users (username, password_hash, email, guest, created_at) VALUES (?, ?, ?, ?, ?)",
            (u, pw_hash, e, 0, datetime.utcnow().isoformat()),
        )
        db.commit()
        session["user"] = u
        flash("Account created and logged in.")
        return redirect(url_for("index"))
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "")
        db = get_db()
        row = db.execute("SELECT username, password_hash FROM users WHERE username = ?", (u,)).fetchone()
        if row and row["password_hash"] and check_password_hash(row["password_hash"], p):
            session["user"] = u
            flash(f"Welcome back, {u}!")
            return redirect(url_for("index"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")


@app.route("/guest")
def guest_login():
    db = get_db()
    while True:
        guest_name = f"Guest_{random.randint(1000, 9999)}"
        if not user_exists(guest_name):
            break
    db.execute(
        "INSERT INTO users (username, password_hash, bio, profile_pic, email, guest, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (guest_name, None, "I am a guest user.", "user.png", None, 1, datetime.utcnow().isoformat()),
    )
    db.commit()
    session["user"] = guest_name
    flash(f"Welcome, {guest_name}! You are logged in as a guest.")
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    u = session.pop("user", None)
    # delete guest user rows
    if u and u.startswith("Guest_"):
        db = get_db()
        db.execute("DELETE FROM users WHERE username = ? AND guest = 1", (u,))
        db.commit()
    flash("Logged out.")
    return redirect(url_for("login"))


@app.route("/index")
@login_required
def index():
    u = session["user"]
    db = get_db()
    posts = db.execute("SELECT p.*, u.profile_pic FROM posts p LEFT JOIN users u ON p.username = u.username WHERE p.type = 'post' ORDER BY p.created_at DESC").fetchall()
    stories = db.execute("SELECT * FROM posts WHERE type = 'story' ORDER BY created_at DESC").fetchall()
    return render_template("index.html", user=u, posts=posts, stories=stories)


@app.route("/explore")
def explore():
    q = request.args.get("query", "").strip().lower()
    results = []
    db = get_db()
    if q:
        rows = db.execute("SELECT username FROM users WHERE lower(username) LIKE ?", (f"%{q}%",)).fetchall()
        for r in rows:
            results.append({"type": "user", "username": r["username"]})
        posts = db.execute("SELECT * FROM posts WHERE lower(caption) LIKE ?", (f"%{q}%",)).fetchall()
        for p in posts:
            results.append({"type": "post", "user": p["username"], "filename": p["filename"], "caption": p["caption"]})
    return render_template("explore.html", user=session.get("user"), results=results, query=q)


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    u = session["user"]
    db = get_db()
    is_guest = db.execute("SELECT guest FROM users WHERE username = ?", (u,)).fetchone()["guest"]
    if request.method == "GET":
        return render_template("upload.html", user=u, guest=bool(is_guest))
    if is_guest:
        return render_template("guest_warning.html", user=u)

    file = request.files.get("file")
    ok, msg = validate_uploaded_file(file)
    if not ok:
        flash(msg)
        return redirect(url_for("upload"))

    saved_name = safe_save_file(file)
    caption = request.form.get("caption", "").strip()
    db.execute(
        "INSERT INTO posts (username, filename, caption, type, created_at) VALUES (?, ?, ?, 'post', ?)",
        (u, saved_name, caption, datetime.utcnow().isoformat()),
    )
    db.commit()
    flash("Post uploaded successfully!")
    return redirect(url_for("index"))


@app.route("/upload_story", methods=["GET", "POST"])
@login_required
def upload_story():
    u = session["user"]
    db = get_db()
    is_guest = db.execute("SELECT guest FROM users WHERE username = ?", (u,)).fetchone()["guest"]
    if request.method == "GET":
        return render_template("story_upload.html", user=u, guest=bool(is_guest))
    if is_guest:
        return render_template("guest_warning.html", user=u)

    file = request.files.get("story")
    ok, msg = validate_uploaded_file(file)
    if not ok:
        flash(msg)
        return redirect(url_for("upload_story"))

    saved_name = safe_save_file(file)
    db.execute(
        "INSERT INTO posts (username, filename, caption, type, created_at) VALUES (?, ?, ?, 'story', ?)",
        (u, saved_name, "", datetime.utcnow().isoformat()),
    )
    db.commit()
    flash("Story uploaded successfully!")
    return redirect(url_for("index"))


@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if not row:
        return "User not found", 404
    current = session.get("user")
    if request.method == "POST":
        if current != username:
            flash("You are not allowed to edit this profile.")
            return redirect(url_for("profile", username=username))
        if row["guest"]:
            flash("Guest users cannot edit profiles.")
            return redirect(url_for("profile", username=username))

        new_u = request.form.get("username", "").strip()
        bio = request.form.get("bio", "")
        pic = request.files.get("profile_pic")

        # username change
        if new_u and new_u != username:
            if user_exists(new_u):
                flash("That username is already taken.")
                return redirect(url_for("profile", username=username))
            # move user record and update posts
            db.execute("UPDATE posts SET username = ? WHERE username = ?", (new_u, username))
            db.execute("UPDATE users SET username = ? WHERE username = ?", (new_u, username))
            db.commit()
            session["user"] = new_u
            username = new_u

        if bio is not None:
            db.execute("UPDATE users SET bio = ? WHERE username = ?", (bio, username))

        if pic and pic.filename:
            ok, msg = validate_uploaded_file(pic)
            if not ok:
                flash(msg)
                return redirect(url_for("profile", username=username))
            name = safe_save_file(pic)
            db.execute("UPDATE users SET profile_pic = ? WHERE username = ?", (name, username))

        db.commit()
        flash("Profile updated.")
        return redirect(url_for("profile", username=username))

    user_posts = db.execute("SELECT * FROM posts WHERE username = ? ORDER BY created_at DESC", (username,)).fetchall()
    return render_template("profile.html", user=current, profile_user=username, user_data=row, posts=user_posts)


@app.route("/like_post/<int:post_id>", methods=["POST"])
def like_post(post_id):
    u = session.get("user")
    if not u:
        return jsonify({"error": "Not logged in"}), 401
    db = get_db()
    r = db.execute("SELECT id FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not r:
        return jsonify({"error": "Post not found"}), 404
    existing = db.execute("SELECT id FROM likes WHERE post_id = ? AND username = ?", (post_id, u)).fetchone()
    if existing:
        db.execute("DELETE FROM likes WHERE id = ?", (existing["id"],))
        db.commit()
        liked = False
    else:
        db.execute("INSERT INTO likes (post_id, username, created_at) VALUES (?, ?, ?)", (post_id, u, datetime.utcnow().isoformat()))
        db.commit()
        liked = True
    likes_count = db.execute("SELECT COUNT(*) as c FROM likes WHERE post_id = ?", (post_id,)).fetchone()["c"]
    return jsonify({"liked": liked, "likes": likes_count})


@app.route("/comment_post/<int:post_id>", methods=["POST"])
def comment_post(post_id):
    u = session.get("user")
    if not u:
        return jsonify({"error": "Not logged in"}), 401
    payload = request.get_json() or {}
    t = (payload.get("comment") or "").strip()
    if not t:
        return jsonify({"error": "Empty comment"}), 400
    db = get_db()
    if not db.execute("SELECT id FROM posts WHERE id = ?", (post_id,)).fetchone():
        return jsonify({"error": "Post not found"}), 404
    db.execute("INSERT INTO comments (post_id, username, text, created_at) VALUES (?, ?, ?, ?)", (post_id, u, t, datetime.utcnow().isoformat()))
    db.commit()
    comments = db.execute("SELECT username, text FROM comments WHERE post_id = ? ORDER BY id", (post_id,)).fetchall()
    return jsonify({"comments": [dict(c) for c in comments]})


@app.route("/delete_post/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    u = session.get("user")
    if not u:
        return jsonify({"error": "Not logged in"}), 401
    db = get_db()
    p = db.execute("SELECT filename, username FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not p or p["username"] != u:
        return jsonify({"error": "Not allowed or post not found"}), 403
    db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    db.commit()
    try:
        os.remove(os.path.join(app.config["UPLOAD_FOLDER"], p["filename"]))
    except Exception:
        pass
    return jsonify({"success": True})


@app.route("/follow/<username>", methods=["POST"])
def follow(username):
    c = session.get("user")
    if not c:
        return jsonify({"error": "Not logged in"}), 401
    if username == c:
        return jsonify({"error": "Cannot follow yourself"}), 400
    db = get_db()
    if not db.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
        return jsonify({"error": "User not found"}), 404
    existing = db.execute("SELECT id FROM followers WHERE username = ? AND follower = ?", (username, c)).fetchone()
    if existing:
        db.execute("DELETE FROM followers WHERE id = ?", (existing["id"],))
        action = "unfollowed"
    else:
        db.execute("INSERT INTO followers (username, follower, created_at) VALUES (?, ?, ?)", (username, c, datetime.utcnow().isoformat()))
        action = "followed"
    db.commit()
    followers_count = db.execute("SELECT COUNT(*) as c FROM followers WHERE username = ?", (username,)).fetchone()["c"]
    return jsonify({"action": action, "followers_count": followers_count})


@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    db = get_db()
    if request.method == "POST":
        d = request.get_json() or {}
        n = d.get("name", "Anonymous") or "Anonymous"
        m = (d.get("message") or "").strip()
        if m:
            db.execute("INSERT INTO feedback (name, message, created_at) VALUES (?, ?, ?)", (n, m, datetime.utcnow().isoformat()))
            db.commit()
        rows = db.execute("SELECT name, message FROM feedback ORDER BY id DESC").fetchall()
        return jsonify([dict(r) for r in rows])
    rows = db.execute("SELECT name, message FROM feedback ORDER BY id DESC").fetchall()
    return render_template("feedback.html", user=session.get("user"), feedbacks=rows)


# -------------------------
# Error handlers
# -------------------------
@app.errorhandler(413)  # Payload Too Large
def too_large(e):
    flash("Uploaded file is too large. Limit is {} MB.".format(app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)))
    return redirect(request.referrer or url_for("index"))


# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "0") in ("1", "true", "True")
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=debug_mode)
