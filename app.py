from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import os, uuid, random
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'change-this-secret-for-production'

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png','jpg','jpeg','gif','mp4','webm','ogg','avi'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

users, posts, stories, feedbacks = {}, [], [], []

@app.route('/')
def splash(): return render_template('splash.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u, p = request.form['username'], request.form['password']
        if u in users and users[u]['password'] == p:
            session['user'] = u
            return redirect(url_for('index'))
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        u, e, p = request.form['username'], request.form['email'], request.form['password']
        if u in users: return render_template('signup.html', error='Username already exists')
        users[u] = {'password':p,'bio':'','profile_pic':'user.png','email':e,
                    'followers':set(),'following':set(),'guest':False}
        session['user'] = u
        return redirect(url_for('index'))
    return render_template('signup.html')

@app.route('/guest')
def guest_login():
    guest_name = f"Guest_{random.randint(1000,9999)}"
    users[guest_name] = {'password':None,'bio':'I am a guest user.','profile_pic':'user.png',
                         'email':None,'followers':set(),'following':set(),'guest':True}
    session['user'] = guest_name
    flash(f'Welcome, {guest_name}! You are logged in as a guest.')
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    u = session.pop('user', None)
    if u and u.startswith('Guest_') and u in users: del users[u]
    return redirect(url_for('login'))

@app.route('/index')
def index():
    if 'user' not in session: return redirect(url_for('login'))
    u = session['user']
    return render_template('index.html', user=u, stories=stories,
                           posts=[p for p in posts if p['type']=='post'],
                           guest=users[u].get('guest',False))

@app.route('/explore')
def explore():
    q = request.args.get('query','').lower()
    results = [{'type':'user','username':u} for u in users if q in u.lower()]
    for p in posts:
        if q in p.get('caption','').lower() and p['type']=='post':
            results.append({'type':'post','user':p['user'],
                            'filename':p['filename'],'caption':p.get('caption')})
    return render_template('explore.html', user=session.get('user'),
                           posts=posts, results=results, query=q)

@app.route('/upload', methods=['GET','POST'])
def upload():
    if 'user' not in session: return redirect(url_for('login'))
    u = session['user']; is_guest = users[u].get('guest',False)
    if request.method == 'GET': return render_template('upload.html', user=u, guest=is_guest)
    if is_guest: return render_template('guest_warning.html', user=u)

    f = request.files.get('file'); cap = request.form.get('caption','')
    if not f or not allowed_file(f.filename):
        flash('Invalid or missing file!'); return redirect(url_for('upload'))
    ext = f.filename.rsplit('.',1)[1].lower(); name = f"{uuid.uuid4()}.{ext}"
    f.save(os.path.join(UPLOAD_FOLDER, name))
    posts.append({'user':u,'filename':name,'caption':cap,'likes':[],'comments':[],'type':'post'})
    flash('Post uploaded successfully!'); return redirect(url_for('index'))

@app.route('/upload_story', methods=['GET','POST'])
def upload_story():
    if 'user' not in session: return redirect(url_for('login'))
    u = session['user']; is_guest = users[u].get('guest',False)
    if request.method == 'GET': return render_template('story_upload.html', user=u, guest=is_guest)
    if is_guest: return render_template('guest_warning.html', user=u)

    s = request.files.get('story')
    if not s or not allowed_file(s.filename):
        flash('Invalid or missing story file!'); return redirect(url_for('upload_story'))
    ext = s.filename.rsplit('.',1)[1].lower(); name = f"{uuid.uuid4()}.{ext}"
    s.save(os.path.join(UPLOAD_FOLDER, name))
    stories.append({'user':u,'filename':name,'type':'story'})
    flash('Story uploaded successfully!'); return redirect(url_for('index'))

@app.route('/profile/<username>', methods=['GET','POST'])
def profile(username):
    if username not in users: return "User not found",404
    ud = users[username]
    if request.method == 'POST' and session.get('user')==username:
        if ud.get('guest'): flash("Guest users cannot edit profiles."); return redirect(url_for('profile', username=username))
        new_u, bio, pic = request.form.get('username'), request.form.get('bio'), request.files.get('profile_pic')
        if new_u and new_u!=username: users[new_u]=users.pop(username); session['user']=new_u; username=new_u
        if bio is not None: users[username]['bio']=bio
        if pic:
            name=str(uuid.uuid4())+'_'+secure_filename(pic.filename)
            pic.save(os.path.join(UPLOAD_FOLDER,name)); users[username]['profile_pic']=name
        return redirect(url_for('profile', username=username))
    user_posts=[p for p in posts if p['user']==username]
    return render_template('profile.html', user=session.get('user'),
                           profile_user=username, user_data=ud, posts=user_posts)

@app.route('/like_post/<filename>', methods=['POST'])
def like_post(filename):
    u=session.get('user'); 
    if not u: return jsonify({'error':'Not logged in'}),401
    for p in posts:
        if p['filename']==filename:
            liked=u not in p['likes']
            if liked: p['likes'].append(u)
            else: p['likes'].remove(u)
            return jsonify({'liked':liked,'likes':len(p['likes'])})
    return jsonify({'error':'Post not found'}),404

@app.route('/comment_post/<filename>', methods=['POST'])
def comment_post(filename):
    u=session.get('user'); 
    if not u: return jsonify({'error':'Not logged in'}),401
    t=request.get_json().get('comment')
    if not t: return jsonify({'error':'Empty comment'}),400
    for p in posts:
        if p['filename']==filename:
            p['comments'].append({'user':u,'text':t})
            return jsonify({'comments':p['comments']})
    return jsonify({'error':'Post not found'}),404

@app.route('/delete_post/<filename>', methods=['POST'])
def delete_post(filename):
    u=session.get('user')
    for p in posts:
        if p['filename']==filename and p['user']==u:
            posts.remove(p)
            try: os.remove(os.path.join(UPLOAD_FOLDER, filename))
            except: pass
            return jsonify({'success':True})
    return jsonify({'error':'Not allowed or post not found'}),403

@app.route('/follow/<username>', methods=['POST'])
def follow(username):
    c=session.get('user')
    if not c: return jsonify({'error':'Not logged in'}),401
    if username not in users: return jsonify({'error':'User not found'}),404
    if username==c: return jsonify({'error':'Cannot follow yourself'}),400
    if c in users[username]['followers']:
        users[username]['followers'].remove(c); users[c]['following'].remove(username); action='unfollowed'
    else:
        users[username]['followers'].add(c); users[c]['following'].add(username); action='followed'
    return jsonify({'action':action,'followers_count':len(users[username]['followers'])})

@app.route('/feedback', methods=['GET','POST'])
def feedback():
    if request.method=='POST':
        d=request.get_json(); n=d.get('name','Anonymous'); m=d.get('message','')
        if m.strip(): feedbacks.append({'name':n,'message':m})
        return jsonify(feedbacks)
    return render_template('feedback.html', user=session.get('user'), feedbacks=feedbacks)

if __name__=='__main__': app.run(debug=True)
