# ================== APP.PY ==================
"""
Complete single-file Instagram-like Flask app (HARNECT) using SQLite.
Features:
 - Signup / Login (passwords hashed)
 - Guest login
 - Upload posts & stories
 - Profile edit (username, bio, profile pic)
 - Like/unlike posts
 - Comment on posts
 - Delete posts/comments
 - Follow/unfollow users
 - Feedback
 - Simple search/explore
 - DB initialization on startup
"""

import os
import uuid
import random
import sqlite3
from functools import wraps
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, g, send_from_directory
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
DATABASE_PATH = os.path.join(BASE_DIR, "harnect.db")

app = Flask(__name__)
app.secret_key = os.environ.get("HARNECT_SECRET_KEY") or os.urandom(24)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB
app.config["SESSION_COOKIE_HTTPONLY"] = True

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
    if db:
        db.close()

def init_db():
    db = sqlite3.connect(DATABASE_PATH)
    c = db.cursor()
    # Users table
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT,
        bio TEXT DEFAULT '',
        profile_pic TEXT DEFAULT 'user.png',
        email TEXT,
        guest INTEGER DEFAULT 0,
        created_at TEXT
    )""")
    # Posts table
    c.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        filename TEXT,
        caption TEXT,
        type TEXT DEFAULT 'post',
        created_at TEXT,
        FOREIGN KEY(username) REFERENCES users(username)
    )""")
    # Followers table
    c.execute("""
    CREATE TABLE IF NOT EXISTS followers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        follower TEXT,
        created_at TEXT
    )""")
    # Likes table
    c.execute("""
    CREATE TABLE IF NOT EXISTS likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        username TEXT,
        created_at TEXT,
        FOREIGN KEY(post_id) REFERENCES posts(id)
    )""")
    # Comments table
    c.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        username TEXT,
        text TEXT,
        created_at TEXT,
        FOREIGN KEY(post_id) REFERENCES posts(id)
    )""")
    # Feedback table
    c.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        message TEXT,
        created_at TEXT
    )""")
    db.commit()
    db.close()

init_db()

# -------------------------
# Helpers
# -------------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def safe_save_file(file, folder=None):
    if folder is None:
        folder = app.config["UPLOAD_FOLDER"]
    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[1].lower()
    new_name = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(folder, new_name))
    return new_name

def validate_uploaded_file(file):
    if not file:
        return False, "No file uploaded"
    if file.filename == "":
        return False, "No file selected"
    if not allowed_file(file.filename):
        return False, f"File type not allowed: {', '.join(ALLOWED_EXTENSIONS)}"
    return True, "OK"

def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped

def user_exists(username):
    db = get_db()
    return bool(db.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone())

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
            (u, pw_hash, e, 0, datetime.utcnow().isoformat())
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
        row = db.execute("SELECT username, password_hash FROM users WHERE username=?", (u,)).fetchone()
        if row and check_password_hash(row["password_hash"], p):
            session["user"] = u
            flash(f"Welcome back, {u}!")
            return redirect(url_for("index"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/guest")
def guest_login():
    db = get_db()
    while True:
        guest_name = f"Guest_{random.randint(1000,9999)}"
        if not user_exists(guest_name):
            break
    db.execute(
        "INSERT INTO users (username, password_hash, bio, profile_pic, email, guest, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (guest_name, None, "I am a guest user.", "user.png", None, 1, datetime.utcnow().isoformat())
    )
    db.commit()
    session["user"] = guest_name
    flash(f"Logged in as guest: {guest_name}")
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    u = session.pop("user", None)
    if u and u.startswith("Guest_"):
        db = get_db()
        db.execute("DELETE FROM users WHERE username=? AND guest=1", (u,))
        db.commit()
    flash("Logged out.")
    return redirect(url_for("login"))

@app.route("/index")
@login_required
def index():
    db = get_db()
    u = session["user"]

    posts = db.execute("""
        SELECT p.*, u.profile_pic,
        (SELECT COUNT(*) FROM likes l WHERE l.post_id=p.id) AS like_count,
        EXISTS(
            SELECT 1 FROM likes l 
            WHERE l.post_id=p.id AND l.username=?
        ) AS liked
        FROM posts p
        LEFT JOIN users u ON p.username=u.username
        WHERE p.type='post'
        ORDER BY p.created_at DESC
    """, (u,)).fetchall()

    # 🔥 ATTACH COMMENTS TO EACH POST
    posts_with_comments = []
    for post in posts:
        comments = db.execute("""
            SELECT id, username, text 
            FROM comments 
            WHERE post_id=? 
            ORDER BY created_at ASC
        """, (post["id"],)).fetchall()

        post = dict(post)
        post["comments"] = comments
        posts_with_comments.append(post)

    stories = db.execute(
        "SELECT * FROM posts WHERE type='story' ORDER BY created_at DESC"
    ).fetchall()

    return render_template(
        "index.html",
        user=u,
        posts=posts_with_comments,
        stories=stories
    )

@app.route("/explore")
@login_required
def explore():
    db = get_db()
    query = request.args.get("query", "").strip()
    results = []
    if query:
        users = db.execute("SELECT username FROM users WHERE username LIKE ? LIMIT 20", (f"%{query}%",)).fetchall()
        results += [{"type": "user", "username": u["username"]} for u in users]
        posts = db.execute(
            "SELECT p.*, u.profile_pic FROM posts p LEFT JOIN users u ON p.username=u.username WHERE p.caption LIKE ? ORDER BY p.created_at DESC LIMIT 20",
            (f"%{query}%",)
        ).fetchall()
        results += [{"type":"post","user":p["username"],"filename":p["filename"],"caption":p["caption"]} for p in posts]
    else:
        posts = db.execute("SELECT p.*, u.profile_pic FROM posts p LEFT JOIN users u ON p.username=u.username ORDER BY p.created_at DESC LIMIT 20").fetchall()
        results += [{"type":"post","user":p["username"],"filename":p["filename"],"caption":p["caption"]} for p in posts]

    return render_template("explore.html", results=results, query=query, user=session.get("user"))

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        f = request.files.get("file")
        caption = request.form.get("caption", "")
        type_post = request.form.get("type", "post")  # 'post' or 'story'

        valid, msg = validate_uploaded_file(f)
        if not valid:
            flash(msg)
            return redirect(request.referrer or url_for("index"))

        filename = safe_save_file(f)
        db = get_db()
        db.execute(
            "INSERT INTO posts (username, filename, caption, type, created_at) VALUES (?, ?, ?, ?, ?)",
            (session["user"], filename, caption, type_post, datetime.utcnow().isoformat())
        )
        db.commit()
        flash(f"{type_post.capitalize()} uploaded successfully!")
        return redirect(url_for("index"))

    return render_template("upload.html", user=session.get("user"))

@app.route("/profile/<username>", methods=["GET", "POST"])
@login_required
def profile(username):
    db = get_db()
    u = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not u:
        flash("User not found")
        return redirect(url_for("index"))

    # ---------------- FOLLOW COUNTS ----------------
    followers_count = db.execute(
        "SELECT COUNT(*) FROM followers WHERE username=?",
        (username,)
    ).fetchone()[0]

    following_count = db.execute(
        "SELECT COUNT(*) FROM followers WHERE follower=?",
        (username,)
    ).fetchone()[0]

    # Check if logged-in user already follows this profile
    is_following = False
    if username != session["user"]:
        is_following = bool(db.execute(
            "SELECT 1 FROM followers WHERE username=? AND follower=?",
            (username, session["user"])
        ).fetchone())

    # ---------------- PROFILE EDIT ----------------
    if request.method == "POST" and username == session["user"]:
        bio = request.form.get("bio", "")
        pic_file = request.files.get("profile_pic")
        if pic_file and allowed_file(pic_file.filename):
            filename = safe_save_file(pic_file)
            db.execute("UPDATE users SET profile_pic=? WHERE username=?", (filename, username))
        db.execute("UPDATE users SET bio=? WHERE username=?", (bio, username))
        db.commit()
        flash("Profile updated")
        return redirect(url_for("profile", username=username))

    posts = db.execute(
        "SELECT * FROM posts WHERE username=? ORDER BY created_at DESC",
        (username,)
    ).fetchall()

    return render_template(
        "profile.html",
        user=session["user"],
        profile=u,
        posts=posts,
        followers_count=followers_count,
        following_count=following_count,
        is_following=is_following
    )

@app.route("/like/<int:post_id>", methods=["POST"])
@login_required
def like_post(post_id):
    db = get_db()
    u = session["user"]
    exists = db.execute("SELECT 1 FROM likes WHERE post_id=? AND username=?", (post_id, u)).fetchone()
    if exists:
        db.execute("DELETE FROM likes WHERE post_id=? AND username=?", (post_id, u))
        liked = False
    else:
        db.execute("INSERT INTO likes (post_id, username, created_at) VALUES (?, ?, ?)", (post_id, u, datetime.utcnow().isoformat()))
        liked = True
    db.commit()

    like_count = db.execute("SELECT COUNT(*) FROM likes WHERE post_id=?", (post_id,)).fetchone()[0]
    return jsonify({'liked': liked, 'like_count': like_count})

@app.route("/comment/<int:post_id>", methods=["POST"])
@login_required
def comment_post(post_id):
    text = request.form.get("comment", "").strip()
    if not text:
        return jsonify({'error': 'Empty comment'}), 400

    db = get_db()
    db.execute("INSERT INTO comments (post_id, username, text, created_at) VALUES (?, ?, ?, ?)",
               (post_id, session["user"], text, datetime.utcnow().isoformat()))
    db.commit()

    return jsonify({'username': session["user"], 'text': text})

@app.route("/delete_post/<int:post_id>", methods=["POST"])
@login_required
def delete_post(post_id):
    db = get_db()
    u = session["user"]
    post = db.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
    if post and post["username"] == u:
        db.execute("DELETE FROM posts WHERE id=?", (post_id,))
        db.execute("DELETE FROM likes WHERE post_id=?", (post_id,))
        db.execute("DELETE FROM comments WHERE post_id=?", (post_id,))
        db.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Not authorized'})


@app.route("/delete_comment/<int:comment_id>", methods=["POST"])
@login_required
def delete_comment(comment_id):
    db = get_db()
    u = session["user"]
    comment = db.execute("SELECT * FROM comments WHERE id=?", (comment_id,)).fetchone()
    if comment and comment["username"] == u:
        db.execute("DELETE FROM comments WHERE id=?", (comment_id,))
        db.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Not authorized'})


@app.route("/follow/<username>")
@login_required
def follow_user(username):
    db = get_db()
    u = session["user"]
    exists = db.execute("SELECT 1 FROM followers WHERE username=? AND follower=?", (username, u)).fetchone()
    if exists:
        db.execute("DELETE FROM followers WHERE username=? AND follower=?", (username, u))
    else:
        db.execute("INSERT INTO followers (username, follower, created_at) VALUES (?, ?, ?)",
                   (username, u, datetime.utcnow().isoformat()))
    db.commit()
    return redirect(request.referrer or url_for("profile", username=username))

@app.route("/feedback", methods=["GET", "POST"])
@login_required
def feedback():
    db = get_db()

    # POST request: add/edit/delete feedback
    if request.method == "POST":
        action = request.form.get("action")  # 'add', 'edit', 'delete'
        feedback_id = request.form.get("id")
        message = request.form.get("message", "").strip()
        user = session.get("user") or "Anonymous"

        if action == "add" and message:
            db.execute(
                "INSERT INTO feedback (name, message, created_at) VALUES (?, ?, ?)",
                (user, message, datetime.utcnow().isoformat())
            )
            db.commit()

        elif action == "edit" and feedback_id and message:
            # Only allow editing own feedback
            db.execute(
                "UPDATE feedback SET message=? WHERE id=? AND name=?",
                (message, feedback_id, user)
            )
            db.commit()

        elif action == "delete" and feedback_id:
            # Only allow deleting own feedback
            db.execute(
                "DELETE FROM feedback WHERE id=? AND name=?",
                (feedback_id, user)
            )
            db.commit()

        # Return updated feedback list for AJAX
        feedbacks = db.execute(
            "SELECT id, name, message FROM feedback ORDER BY created_at DESC"
        ).fetchall()
        feedback_list = [
            {"id": f["id"], "name": f["name"], "message": f["message"]}
            for f in feedbacks
        ]
        return jsonify(feedback_list)

    # GET request: show page
    feedbacks = db.execute(
        "SELECT id, name, message FROM feedback ORDER BY created_at DESC"
    ).fetchall()
    return render_template("feedback.html", feedbacks=feedbacks, user=session.get("user"))

@app.errorhandler(413)
def too_large(e):
    flash(f"File too large. Limit: {app.config['MAX_CONTENT_LENGTH']//(200*1024*1024)} MB")
    return redirect(request.referrer or url_for("index"))

# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
