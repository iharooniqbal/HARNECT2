# app.py 
import os
import uuid
import random
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, flash, abort
)
from werkzeug.utils import secure_filename

# -------------------------
# Configuration
# -------------------------
app = Flask(__name__)

# Secret key must come from environment in production.
# If not set, a random key will be used (not suitable across restarts).
app.secret_key = os.environ.get("HARNECT_SECRET_KEY") or os.urandom(24)

# Upload settings
BASE_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Allowed extensions and a simple mimetype mapping
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "mp4", "webm", "ogg", "avi"}
ALLOWED_MIMETYPE_PREFIX = ("image/", "video/")

# Limit upload size to 50 MB (adjust if needed)
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("HARNECT_MAX_UPLOAD_MB", 50)) * 1024 * 1024

# Session cookie security (set true in production behind HTTPS)
app.config["SESSION_COOKIE_HTTPONLY"] = True
# app.config["SESSION_COOKIE_SECURE"] = True  # enable in production with HTTPS

# Helper in-memory stores (dev only). Use a DB for production.
users = {}
posts = []
stories = []
feedbacks = []

# -------------------------
# Helpers
# -------------------------
def allowed_file(filename: str) -> bool:
    """Check extension only."""
    return (
        isinstance(filename, str)
        and "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )

def safe_save_file(storage_file, target_folder=UPLOAD_FOLDER):
    """
    Save an uploaded FileStorage object to disk with a UUID-prefixed secure filename.
    Returns the saved filename.
    """
    filename = secure_filename(storage_file.filename)
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    new_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    dest = os.path.join(target_folder, new_name)
    storage_file.save(dest)
    return new_name

def validate_uploaded_file(storage_file):
    """
    Returns (ok:bool, message:str)
    Performs:
      - presence check
      - extension check
      - simple mimetype prefix check (image/ or video/)
    Note: mimetype is provided by the client; for stronger security use python-magic.
    """
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

# -------------------------
# Routes
# -------------------------
@app.route("/")
def splash():
    return render_template("splash.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "")
        user = users.get(u)
        if user and user.get("password") == p:
            session["user"] = u
            flash(f"Welcome back, {u}!")
            return redirect(url_for("index"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        e = request.form.get("email", "").strip() or None
        p = request.form.get("password", "")
        if not u or not p:
            return render_template("signup.html", error="Username and password required")
        if u in users:
            return render_template("signup.html", error="Username already exists")
        # initialize user object
        users[u] = {
            "password": p,
            "bio": "",
            "profile_pic": "user.png",
            "email": e,
            "followers": set(),
            "following": set(),
            "guest": False,
        }
        session["user"] = u
        flash("Account created and logged in.")
        return redirect(url_for("index"))
    return render_template("signup.html")

@app.route("/guest")
def guest_login():
    # create unique guest username
    while True:
        guest_name = f"Guest_{random.randint(1000, 9999)}"
        if guest_name not in users:
            break
    users[guest_name] = {
        "password": None,
        "bio": "I am a guest user.",
        "profile_pic": "user.png",
        "email": None,
        "followers": set(),
        "following": set(),
        "guest": True,
    }
    session["user"] = guest_name
    flash(f"Welcome, {guest_name}! You are logged in as a guest.")
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    u = session.pop("user", None)
    # cleanup temporary guest user data
    if u and u.startswith("Guest_") and users.get(u, {}).get("guest"):
        users.pop(u, None)
    flash("Logged out.")
    return redirect(url_for("login"))
    
@app.route("/index")
@login_required
def index():
    u = session["user"]
    return render_template(
        "index.html",
        user=u,
        stories=stories,
        posts=[p for p in posts if p.get("type") == "post"],
        guest=users.get(u, {}).get("guest", False),
    )

@app.route("/explore")
def explore():
    q = request.args.get("query", "").strip().lower()
    results = []
    if q:
        for username in users:
            if q in username.lower():
                results.append({"type": "user", "username": username})
        for p in posts:
            if p.get("type") == "post" and q in p.get("caption", "").lower():
                results.append(
                    {
                        "type": "post",
                        "user": p.get("user"),
                        "filename": p.get("filename"),
                        "caption": p.get("caption"),
                    }
                )
    return render_template("explore.html", user=session.get("user"), posts=posts, results=results, query=q)

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    u = session["user"]
    is_guest = users.get(u, {}).get("guest", False)
    if request.method == "GET":
        return render_template("upload.html", user=u, guest=is_guest)
    if is_guest:
        return render_template("guest_warning.html", user=u)

    file = request.files.get("file")
    ok, msg = validate_uploaded_file(file)
    if not ok:
        flash(msg)
        return redirect(url_for("upload"))

    saved_name = safe_save_file(file)
    caption = request.form.get("caption", "").strip()
    posts.append(
        {"user": u, "filename": saved_name, "caption": caption, "likes": [], "comments": [], "type": "post"}
    )
    flash("Post uploaded successfully!")
    return redirect(url_for("index"))

@app.route("/upload_story", methods=["GET", "POST"])
@login_required
def upload_story():
    u = session["user"]
    is_guest = users.get(u, {}).get("guest", False)
    if request.method == "GET":
        return render_template("story_upload.html", user=u, guest=is_guest)
    if is_guest:
        return render_template("guest_warning.html", user=u)

    file = request.files.get("story")
    ok, msg = validate_uploaded_file(file)
    if not ok:
        flash(msg)
        return redirect(url_for("upload_story"))

    saved_name = safe_save_file(file)
    stories.append({"user": u, "filename": saved_name, "type": "story"})
    flash("Story uploaded successfully!")
    return redirect(url_for("index"))

@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    if username not in users:
        return "User not found", 404
    ud = users[username]
    current = session.get("user")
    if request.method == "POST":
        # Only the owner can edit their profile
        if current != username:
            flash("You are not allowed to edit this profile.")
            return redirect(url_for("profile", username=username))
        if ud.get("guest"):
            flash("Guest users cannot edit profiles.")
            return redirect(url_for("profile", username=username))

        new_u = request.form.get("username", "").strip()
        bio = request.form.get("bio", "")
        pic = request.files.get("profile_pic")

        # username change: ensure not taken
        if new_u and new_u != username:
            if new_u in users:
                flash("That username is already taken.")
                return redirect(url_for("profile", username=username))
            # move user data, and update posts/stories ownership
            users[new_u] = users.pop(username)
            # update posts/stories to reflect new username
            for p in posts:
                if p.get("user") == username:
                    p["user"] = new_u
            for s in stories:
                if s.get("user") == username:
                    s["user"] = new_u
            session["user"] = new_u
            username = new_u
            ud = users[username]

        if bio is not None:
            users[username]["bio"] = bio

        if pic and pic.filename:
            ok, msg = validate_uploaded_file(pic)
            if not ok:
                flash(msg)
                return redirect(url_for("profile", username=username))
            name = safe_save_file(pic)
            users[username]["profile_pic"] = name

        flash("Profile updated.")
        return redirect(url_for("profile", username=username))

    user_posts = [p for p in posts if p.get("user") == username]
    return render_template(
        "profile.html",
        user=current,
        profile_user=username,
        user_data=ud,
        posts=user_posts,
    )

@app.route("/like_post/<filename>", methods=["POST"])
def like_post(filename):
    u = session.get("user")
    if not u:
        return jsonify({"error": "Not logged in"}), 401
    for p in posts:
        if p.get("filename") == filename:
            if u in p.get("likes", []):
                p["likes"].remove(u)
                liked = False
            else:
                p["likes"].append(u)
                liked = True
            return jsonify({"liked": liked, "likes": len(p.get("likes", []))})
    return jsonify({"error": "Post not found"}), 404

@app.route("/comment_post/<filename>", methods=["POST"])
def comment_post(filename):
    u = session.get("user")
    if not u:
        return jsonify({"error": "Not logged in"}), 401
    payload = request.get_json() or {}
    t = (payload.get("comment") or "").strip()
    if not t:
        return jsonify({"error": "Empty comment"}), 400
    for p in posts:
        if p.get("filename") == filename:
            p.setdefault("comments", []).append({"user": u, "text": t})
            return jsonify({"comments": p.get("comments", [])})
    return jsonify({"error": "Post not found"}), 404

@app.route("/delete_post/<filename>", methods=["POST"])
def delete_post(filename):
    u = session.get("user")
    if not u:
        return jsonify({"error": "Not logged in"}), 401
    for p in list(posts):
        if p.get("filename") == filename and p.get("user") == u:
            posts.remove(p)
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, filename))
            except Exception:
                pass
            return jsonify({"success": True})
    return jsonify({"error": "Not allowed or post not found"}), 403

@app.route("/follow/<username>", methods=["POST"])
def follow(username):
    c = session.get("user")
    if not c:
        return jsonify({"error": "Not logged in"}), 401
    if username not in users:
        return jsonify({"error": "User not found"}), 404
    if username == c:
        return jsonify({"error": "Cannot follow yourself"}), 400

    # Ensure follower/following sets exist
    users[username].setdefault("followers", set())
    users[c].setdefault("following", set())

    if c in users[username]["followers"]:
        users[username]["followers"].remove(c)
        users[c]["following"].remove(username)
        action = "unfollowed"
    else:
        users[username]["followers"].add(c)
        users[c]["following"].add(username)
        action = "followed"

    return jsonify({"action": action, "followers_count": len(users[username]["followers"])})

@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if request.method == "POST":
        d = request.get_json() or {}
        n = d.get("name", "Anonymous") or "Anonymous"
        m = (d.get("message") or "").strip()
        if m:
            feedbacks.append({"name": n, "message": m})
        return jsonify(feedbacks)
    return render_template("feedback.html", user=session.get("user"), feedbacks=feedbacks)

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
    # Use env var FLASK_DEBUG to control debug mode. Default to False for safety.
    debug_mode = os.environ.get("FLASK_DEBUG", "0") in ("1", "true", "True")
    # In dev, host=127.0.0.1 is fine; change if you need external access.
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=debug_mode)


from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "your_secret_key"

def get_db():
    conn = sqlite3.connect("harnect.db")
    conn.row_factory = sqlite3.Row
    return conn

import sqlite3

conn = sqlite3.connect("harnect.db")
conn.execute("""
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    content TEXT
);
""")
conn.close()


@app.route("/post", methods=["POST"])
def post():
    if "user" not in session:
        return redirect("/login")

    content = request.form["content"]

    db = get_db()
    db.execute("INSERT INTO posts (username, content) VALUES (?, ?)", 
               (session["user"], content))
    db.commit()

    return redirect("/")
    
@app.route("/")
def home():
    db = get_db()
    posts = db.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()
    return render_template("home.html", posts=posts)
