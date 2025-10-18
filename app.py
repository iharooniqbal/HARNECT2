from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import os, uuid, random
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'change-this-secret-for-production'

# -------------------------
# FILE UPLOAD SETTINGS
# -------------------------
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm', 'ogg', 'avi'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# -------------------------
# IN-MEMORY DATABASE
# -------------------------
users = {}   # username -> user data
posts = []   # all uploaded posts
stories = [] # all uploaded stories
feedbacks = []  # feedback messages

# -------------------------
# AUTH ROUTES
# -------------------------
@app.route('/')
def splash():
    return render_template('splash.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        if u in users and users[u]['password'] == p:
            session['user'] = u
            return redirect(url_for('index'))
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        u = request.form['username']
        e = request.form['email']
        p = request.form['password']
        if u in users:
            return render_template('signup.html', error='Username already exists')
        users[u] = {
            'password': p,
            'bio': '',
            'profile_pic': 'user.png',
            'email': e,
            'followers': set(),
            'following': set(),
            'guest': False
        }
        session['user'] = u
        return redirect(url_for('index'))
    return render_template('signup.html')

# -------------------------
# GUEST USER OPTION
# -------------------------
@app.route('/guest')
def guest_login():
    # Generate unique guest username
    guest_name = f"Guest_{random.randint(1000, 9999)}"
    session['user'] = guest_name

    users[guest_name] = {
        'password': None,
        'bio': 'I am a guest user.',
        'profile_pic': 'user.png',
        'email': None,
        'followers': set(),
        'following': set(),
        'guest': True
    }

    flash(f'Welcome, {guest_name}! You are logged in as a guest.')
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    user = session.pop('user', None)
    if user and user.startswith('Guest_') and user in users:
        del users[user]  # Remove guest data after logout
    return redirect(url_for('login'))

# -------------------------
# MAIN ROUTES
# -------------------------
@app.route('/index')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))

    story_posts = [p for p in stories]
    feed_posts = [p for p in posts if p['type'] == 'post']

    return render_template(
        'index.html',
        user=session['user'],
        stories=story_posts,
        posts=feed_posts,
        guest=users[session['user']].get('guest', False)
    )

@app.route('/explore')
def explore():
    query = request.args.get('query', '')
    results = []
    for u, data in users.items():
        if query.lower() in u.lower():
            results.append({'type': 'user', 'username': u})
    for p in posts:
        if query.lower() in p.get('caption', '').lower() and p['type'] == 'post':
            results.append({'type': 'post', 'user': p['user'], 'filename': p['filename'], 'caption': p.get('caption')})
    return render_template('explore.html', user=session.get('user'), posts=posts, results=results, query=query)

# -------------------------
# UPLOAD ROUTES
# -------------------------
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user' not in session:
        return redirect(url_for('login'))

    current_user = session['user']
    is_guest = users[current_user].get('guest', False)

    # If GET request → show upload page
    if request.method == 'GET':
        return render_template('upload.html', user=current_user, guest=is_guest)

    # 🛑 If guest tries to upload → show warning page
    if is_guest:
        return render_template('guest_warning.html', user=current_user)

    # 🟢 Normal upload for logged-in users
    file = request.files.get('file')
    caption = request.form.get('caption', '')

    if not file or not allowed_file(file.filename):
        flash('Invalid or missing file!')
        return redirect(url_for('upload'))

    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4()}.{ext}"
    save_path = os.path.join(UPLOAD_FOLDER, unique_name)
    file.save(save_path)

    posts.append({
        'user': current_user,
        'filename': unique_name,
        'caption': caption,
        'likes': [],
        'comments': [],
        'type': 'post'
    })

    flash('Post uploaded successfully!')
    return redirect(url_for('index'))


@app.route('/upload_story', methods=['GET', 'POST'])
def upload_story():
    if 'user' not in session:
        return redirect(url_for('login'))

    current_user = session['user']
    is_guest = users[current_user].get('guest', False)

    # If GET → show story upload page
    if request.method == 'GET':
        return render_template('story_upload.html', user=current_user, guest=is_guest)

    # 🛑 If guest tries to upload story
    if is_guest:
        return render_template('guest_warning.html', user=current_user)

    # 🟢 Normal story upload for logged-in users
    story_file = request.files.get('story')

    if not story_file or not allowed_file(story_file.filename):
        flash('Invalid or missing story file!')
        return redirect(url_for('upload_story'))

    filename = secure_filename(story_file.filename)
    ext = filename.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4()}.{ext}"
    save_path = os.path.join(UPLOAD_FOLDER, unique_name)
    story_file.save(save_path)

    stories.append({
        'user': current_user,
        'filename': unique_name,
        'type': 'story'
    })

    flash('Story uploaded successfully!')
    return redirect(url_for('index'))

# -------------------------
# PROFILE
# -------------------------
@app.route('/profile/<username>', methods=['GET','POST'])
def profile(username):
    if username not in users:
        return "User not found", 404
    user_data = users[username]

    if request.method == 'POST' and session.get('user') == username:
        if user_data.get('guest'):
            flash("Guest users cannot edit profiles.")
            return redirect(url_for('profile', username=username))

        new_username = request.form.get('username')
        bio = request.form.get('bio')
        profile_pic_file = request.files.get('profile_pic')

        if new_username and new_username != username:
            users[new_username] = users.pop(username)
            session['user'] = new_username
            username = new_username
        if bio is not None:
            users[username]['bio'] = bio
        if profile_pic_file:
            filename = str(uuid.uuid4()) + '_' + secure_filename(profile_pic_file.filename)
            profile_pic_file.save(os.path.join(UPLOAD_FOLDER, filename))
            users[username]['profile_pic'] = filename
        return redirect(url_for('profile', username=username))

    user_posts = [p for p in posts if p['user'] == username]
    return render_template('profile.html', user=session.get('user'), profile_user=username, user_data=user_data, posts=user_posts)

# -------------------------
# LIKE / COMMENT / DELETE
# -------------------------
@app.route('/like_post/<filename>', methods=['POST'])
def like_post(filename):
    u = session.get('user')
    if not u:
        return jsonify({'error': 'Not logged in'}), 401
    for p in posts:
        if p['filename'] == filename:
            if u in p['likes']:
                p['likes'].remove(u)
                liked = False
            else:
                p['likes'].append(u)
                liked = True
            return jsonify({'liked': liked, 'likes': len(p['likes'])})
    return jsonify({'error': 'Post not found'}), 404

@app.route('/comment_post/<filename>', methods=['POST'])
def comment_post(filename):
    u = session.get('user')
    if not u:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.get_json()
    text = data.get('comment')
    if not text:
        return jsonify({'error': 'Empty comment'}), 400
    for p in posts:
        if p['filename'] == filename:
            p['comments'].append({'user': u, 'text': text})
            return jsonify({'comments': p['comments']})
    return jsonify({'error': 'Post not found'}), 404

@app.route('/delete_post/<filename>', methods=['POST'])
def delete_post(filename):
    u = session.get('user')
    for p in posts:
        if p['filename'] == filename and p['user'] == u:
            posts.remove(p)
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, filename))
            except:
                pass
            return jsonify({'success': True})
    return jsonify({'error': 'Not allowed or post not found'}), 403

# -------------------------
# FOLLOW / UNFOLLOW
# -------------------------
@app.route('/follow/<username>', methods=['POST'])
def follow(username):
    current_user = session.get('user')
    if not current_user:
        return jsonify({'error': 'Not logged in'}), 401
    if username not in users:
        return jsonify({'error': 'User not found'}), 404
    if username == current_user:
        return jsonify({'error': 'Cannot follow yourself'}), 400

    if current_user in users[username]['followers']:
        users[username]['followers'].remove(current_user)
        users[current_user]['following'].remove(username)
        action = 'unfollowed'
    else:
        users[username]['followers'].add(current_user)
        users[current_user]['following'].add(username)
        action = 'followed'

    return jsonify({
        'action': action,
        'followers_count': len(users[username]['followers'])
    })

# -------------------------
# FEEDBACK
# -------------------------
@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        data = request.get_json()
        name = data.get('name', 'Anonymous')
        message = data.get('message', '')
        if message.strip():
            feedbacks.append({'name': name, 'message': message})
        return jsonify(feedbacks)
    return render_template('feedback.html', user=session.get('user'), feedbacks=feedbacks)

# -------------------------
# RUN APP
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)
