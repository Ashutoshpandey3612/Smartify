import os
import sqlite3
import time
from functools import wraps
from flask import Flask, render_template_string, request, redirect, session, url_for, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "smartify_secret_key_change_later")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "smartify.db")
SONG_FOLDER = os.path.join(BASE_DIR, "static", "songs")
COVER_FOLDER = os.path.join(BASE_DIR, "static", "covers")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(SONG_FOLDER, exist_ok=True)
os.makedirs(COVER_FOLDER, exist_ok=True)

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

ALLOWED_AUDIO = {"mp3", "wav", "ogg", "m4a"}
ALLOWED_IMAGE = {"png", "jpg", "jpeg", "webp"}

def allowed_file(filename, allowed):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'customer'
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS songs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        artist TEXT NOT NULL,
        mood TEXT NOT NULL,
        filename TEXT NOT NULL,
        cover TEXT DEFAULT '',
        play_count INTEGER DEFAULT 0,
        like_count INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS likes(
        username TEXT NOT NULL,
        song_id INTEGER NOT NULL,
        UNIQUE(username, song_id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS history(
        username TEXT NOT NULL,
        song_id INTEGER NOT NULL,
        played_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("SELECT * FROM users WHERE username=?", (ADMIN_USERNAME,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users(username,password,role) VALUES(?,?,?)",
            (ADMIN_USERNAME, ADMIN_PASSWORD, "admin")
        )

    con.commit()
    con.close()

init_db()

CSS = """
<style>
*{box-sizing:border-box}
body{margin:0;background:#000;color:white;font-family:Arial, sans-serif}
a{text-decoration:none;color:inherit}
.page{min-height:100vh;display:grid;grid-template-columns:270px 1fr;gap:10px;padding:10px}
.sidebar{background:#121212;border-radius:18px;padding:24px;display:flex;flex-direction:column;justify-content:space-between}
.logo{font-size:32px;font-weight:900;color:#1DB954;margin-bottom:25px}
.nav a{display:block;padding:13px 10px;border-radius:12px;margin:6px 0;color:#ddd;font-weight:700}
.nav a:hover{background:#242424;color:white}
.main{background:linear-gradient(#222,#101010 35%,#000);border-radius:18px;overflow:auto}
.topbar{height:72px;background:#101010;display:flex;justify-content:space-between;align-items:center;padding:0 28px;position:sticky;top:0;z-index:10}
.search input{width:380px;background:#242424;color:white;border:0;border-radius:30px;padding:14px 20px}
.btn{background:#1DB954;border:0;color:white;padding:12px 18px;border-radius:28px;font-weight:800;cursor:pointer}
.btn.white{background:white;color:#000}
.btn.red{background:#e63946}
.content{padding:28px}
.hero{background:linear-gradient(135deg,#1DB954,#0f3d20);border-radius:22px;padding:28px;margin-bottom:26px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:18px}
.row{display:flex;gap:18px;overflow-x:auto;padding-bottom:20px}
.card{background:#181818;border-radius:16px;padding:15px;min-width:210px}
.card:hover{background:#282828}
.cover{width:100%;height:155px;border-radius:12px;object-fit:cover;background:#1DB954;display:flex;align-items:center;justify-content:center;font-weight:900}
.muted{color:#b3b3b3}
audio{width:100%;height:36px;margin-top:10px}
.small{display:inline-block;background:#333;padding:8px 10px;border-radius:20px;margin-top:8px;font-size:13px}
.formbox{background:#181818;padding:22px;border-radius:18px;margin-bottom:20px}
input,select{padding:13px;border-radius:14px;border:0;margin:7px;background:#242424;color:white}
label{display:block;margin-top:10px;color:#bbb}
table{width:100%;border-collapse:collapse;background:#181818;border-radius:16px;overflow:hidden}
td,th{padding:14px;border-bottom:1px solid #333;text-align:left}
.auth{height:100vh;display:flex;align-items:center;justify-content:center;background:#121212}
.authbox{width:360px;background:#181818;padding:34px;border-radius:22px;text-align:center}
.authbox input{width:92%}
.flash{background:#2b2b2b;border-left:5px solid #1DB954;padding:12px;border-radius:12px;margin-bottom:15px}
@media(max-width:800px){
.page{grid-template-columns:1fr}
.sidebar{display:block}
.search input{width:210px}
}
@media (max-width: 800px) {

  body {
    background: radial-gradient(circle at top, #5b3c88, #171717 60%, #000);
  }

  .page {
    display: block;
    padding: 0;
  }

  .sidebar {
    display: none;
  }

  .main {
    min-height: 100vh;
    border-radius: 0;
    background: linear-gradient(160deg, rgba(255,255,255,0.18), rgba(255,255,255,0.05));
    backdrop-filter: blur(20px);
  }

  .topbar {
    height: auto;
    padding: 18px;
    background: transparent;
    display: block;
  }

  .search input {
    width: 100%;
    background: rgba(255,255,255,0.18);
    backdrop-filter: blur(15px);
  }

  .content {
    padding: 18px;
  }

  .hero {
    border-radius: 28px;
    background: rgba(255,255,255,0.14);
    backdrop-filter: blur(22px);
    box-shadow: 0 20px 60px rgba(0,0,0,0.35);
  }

  .grid {
    display: block;
  }

  .row {
    display: block;
    overflow: visible;
  }

  .card {
    width: 100%;
    min-width: 0;
    margin-bottom: 18px;
    border-radius: 26px;
    background: rgba(255,255,255,0.13);
    backdrop-filter: blur(22px);
    box-shadow: 0 20px 45px rgba(0,0,0,0.35);
  }

  .cover {
    height: 260px;
    border-radius: 26px;
  }

  audio {
    margin-top: 14px;
  }

  .small {
    background: rgba(255,255,255,0.18);
  }

  h1, h2, h3 {
    color: white;
  }
}
</style>


"""

BASE_HTML_START = """
<!DOCTYPE html>
<html>
<head>
<title>Smartify</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
""" + CSS + """
</head>
<body>
"""

AUTH_HTML = BASE_HTML_START + """
<div class="auth">
<div class="authbox">
<h1 class="logo">🎧 Smartify</h1>
<h2>{{title}}</h2>
{% with messages = get_flashed_messages() %}
{% if messages %}
{% for m in messages %}<div class="flash">{{m}}</div>{% endfor %}
{% endif %}
{% endwith %}
<form method="POST">
<input name="username" placeholder="Username" required>
<input name="password" type="password" placeholder="Password" required>
<button class="btn">{{title}}</button>
</form>
{% if title == "Login" %}
<p class="muted">New customer? <a style="color:#1DB954" href="/register">Register</a></p>
<p class="muted">Developer login: admin / admin123</p>
{% else %}
<p class="muted">Already have account? <a style="color:#1DB954" href="/">Login</a></p>
{% endif %}
</div>
</div>
</body>
</html>
"""

def layout(content):
    return BASE_HTML_START + """
<div class="page">
<div class="sidebar">
<div>
<div class="logo">🎧 Smartify</div>
<div class="nav">
<a href="/home">🏠 Home</a>
<a href="/liked">❤️ Liked Songs</a>
<a href="/history">🕘 History</a>
{% if role == 'admin' %}
<a href="/admin">🛠 Developer Panel</a>
{% endif %}
<a href="/logout">🚪 Logout</a>
</div>
</div>
<div class="muted">Logged in as<br><b>{{user}}</b><br>Role: {{role}}</div>
</div>

<div class="main">
<div class="topbar">
<form class="search" method="GET" action="/home">
<input name="q" value="{{q or ''}}" placeholder="🔍 Search songs or artists">
<button class="btn">Search</button>
</form>
<a class="btn white" href="/logout">Logout</a>
</div>
<div class="content">
{% with messages = get_flashed_messages() %}
{% if messages %}
{% for m in messages %}<div class="flash">{{m}}</div>{% endfor %}
{% endif %}
{% endwith %}
""" + content + """
</div>
</div>
</div>

<script>
const audios = document.querySelectorAll(".smart-audio");
audios.forEach(audio => {
  audio.addEventListener("play", function(){
    audios.forEach(other => {
      if(other !== audio){
        other.pause();
        other.currentTime = 0;
      }
    });
  });
});
</script>

</body>
</html>
"""

HOME_HTML = layout("""
<div class="hero">
<h1>Welcome to Smartify 🎶</h1>
<p>Spotify-style Smart Music System. Developer uploads songs, customers listen, like and track history.</p>
<form method="GET" action="/home">
<select name="mood">
<option value="">All moods</option>
<option value="happy" {% if mood=='happy' %}selected{% endif %}>😊 Happy</option>
<option value="sad" {% if mood=='sad' %}selected{% endif %}>😔 Sad</option>
<option value="angry" {% if mood=='angry' %}selected{% endif %}>😡 Angry</option>
<option value="romantic" {% if mood=='romantic' %}selected{% endif %}>❤️ Romantic</option>
<option value="relax" {% if mood=='relax' %}selected{% endif %}>🌿 Relax</option>
</select>
<button class="btn">Recommend</button>
</form>
</div>

<h2>🔥 Trending Songs</h2>
<div class="row">
{% for s in trending %}
<div class="card">
{% if s.cover %}
<img class="cover" src="/static/covers/{{s.cover}}">
{% else %}
<div class="cover">Album Cover</div>
{% endif %}
<h3>{{s.title}}</h3>
<p class="muted">{{s.artist}} · {{s.mood}}</p>
<p class="muted">▶ {{s.play_count}} · ❤️ {{s.like_count}}</p>
<audio controls class="smart-audio">
<source src="/static/songs/{{s.filename}}">
</audio>
<a class="small" href="/play/{{s.id}}">▶ Add History</a>
<a class="small" href="/like/{{s.id}}">❤️ Like</a>
</div>
{% else %}
<p class="muted">No songs yet. Developer should upload songs.</p>
{% endfor %}
</div>

<h2>🎧 Songs</h2>
<div class="grid">
{% for s in songs %}
<div class="card">
{% if s.cover %}
<img class="cover" src="/static/covers/{{s.cover}}">
{% else %}
<div class="cover">Album Cover</div>
{% endif %}
<h3>{{s.title}}</h3>
<p class="muted">{{s.artist}} · {{s.mood}}</p>
<audio controls class="smart-audio">
<source src="/static/songs/{{s.filename}}">
</audio>
<a class="small" href="/play/{{s.id}}">▶ Add History</a>
<a class="small" href="/like/{{s.id}}">❤️ Like</a>
</div>
{% else %}
<div class="card"><h3>No songs found</h3><p class="muted">Try another mood or search.</p></div>
{% endfor %}
</div>
""")

ADMIN_HTML = layout("""
<div class="hero">
<h1>🛠 Developer Panel</h1>
<p>You are the developer/admin. Upload songs here. Customers will see them on Home.</p>
</div>

<div class="formbox">
<h2>➕ Upload New Song</h2>
<form method="POST" action="/admin/add-song" enctype="multipart/form-data">
<label>Song Title</label>
<input name="title" placeholder="Example: My Song" required>
<label>Artist Name</label>
<input name="artist" placeholder="Example: Arijit Singh" required>
<label>Mood</label>
<select name="mood" required>
<option value="happy">Happy</option>
<option value="sad">Sad</option>
<option value="angry">Angry</option>
<option value="romantic">Romantic</option>
<option value="relax">Relax</option>
</select>
<label>Song File</label>
<input type="file" name="songfile" accept="audio/*" required>
<label>Cover Image Optional</label>
<input type="file" name="coverfile" accept="image/*">
<br>
<button class="btn">Upload Song</button>
</form>
</div>

<h2>All Songs</h2>
<table>
<tr>
<th>Title</th><th>Artist</th><th>Mood</th><th>Plays</th><th>Likes</th><th>Action</th>
</tr>
{% for s in songs %}
<tr>
<td>{{s.title}}</td>
<td>{{s.artist}}</td>
<td>{{s.mood}}</td>
<td>{{s.play_count}}</td>
<td>{{s.like_count}}</td>
<td><a class="small" href="/admin/delete/{{s.id}}">Delete</a></td>
</tr>
{% endfor %}
</table>
""")

LIST_HTML = layout("""
<h1>{{title}}</h1>
<div class="grid">
{% for s in data %}
<div class="card">
{% if s.cover %}
<img class="cover" src="/static/covers/{{s.cover}}">
{% else %}
<div class="cover">Album Cover</div>
{% endif %}
<h3>{{s.title}}</h3>
<p class="muted">{{s.artist}}</p>
<audio controls class="smart-audio">
<source src="/static/songs/{{s.filename}}">
</audio>
</div>
{% else %}
<p class="muted">No data found.</p>
{% endfor %}
</div>
""")

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect("/")
        return func(*args, **kwargs)
    return wrapper

def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect("/")
        if session.get("role") != "admin":
            flash("Only developer/admin can access this page.")
            return redirect("/home")
        return func(*args, **kwargs)
    return wrapper

@app.context_processor
def inject_user():
    return {
        "user": session.get("user", ""),
        "role": session.get("role", "")
    }

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        con = db()
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cur.fetchone()
        con.close()

        if user:
            session["user"] = user["username"]
            session["role"] = user["role"]
            return redirect("/admin" if user["role"] == "admin" else "/home")

        flash("Wrong username or password.")
    return render_template_string(AUTH_HTML, title="Login")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        try:
            con = db()
            cur = con.cursor()
            cur.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)", (username, password, "customer"))
            con.commit()
            con.close()
            flash("Account created. Please login.")
            return redirect("/")
        except sqlite3.IntegrityError:
            flash("Username already exists.")
    return render_template_string(AUTH_HTML, title="Register")

@app.route("/home")
@login_required
def home():
    q = request.args.get("q", "").strip()
    mood = request.args.get("mood", "").strip()

    con = db()
    cur = con.cursor()

    if q:
        cur.execute("SELECT * FROM songs WHERE title LIKE ? OR artist LIKE ? ORDER BY id DESC", (f"%{q}%", f"%{q}%"))
    elif mood:
        cur.execute("SELECT * FROM songs WHERE mood=? ORDER BY id DESC", (mood,))
    else:
        cur.execute("SELECT * FROM songs ORDER BY id DESC")

    songs = cur.fetchall()
    cur.execute("SELECT * FROM songs ORDER BY play_count DESC, like_count DESC, id DESC LIMIT 8")
    trending = cur.fetchall()
    con.close()

    return render_template_string(HOME_HTML, songs=songs, trending=trending, q=q, mood=mood)

@app.route("/play/<int:song_id>")
@login_required
def play(song_id):
    con = db()
    cur = con.cursor()
    cur.execute("INSERT INTO history(username, song_id) VALUES(?,?)", (session["user"], song_id))
    cur.execute("UPDATE songs SET play_count = play_count + 1 WHERE id=?", (song_id,))
    con.commit()
    con.close()
    return redirect(request.referrer or "/home")

@app.route("/like/<int:song_id>")
@login_required
def like(song_id):
    con = db()
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO likes(username, song_id) VALUES(?,?)", (session["user"], song_id))
        cur.execute("UPDATE songs SET like_count = like_count + 1 WHERE id=?", (song_id,))
        con.commit()
    except sqlite3.IntegrityError:
        flash("Already liked.")
    con.close()
    return redirect(request.referrer or "/home")

@app.route("/liked")
@login_required
def liked():
    con = db()
    cur = con.cursor()
    cur.execute("""
    SELECT songs.* FROM likes
    JOIN songs ON likes.song_id = songs.id
    WHERE likes.username=?
    ORDER BY likes.rowid DESC
    """, (session["user"],))
    data = cur.fetchall()
    con.close()
    return render_template_string(LIST_HTML, title="Liked Songs", data=data, q="", mood="")

@app.route("/history")
@login_required
def history():
    con = db()
    cur = con.cursor()
    cur.execute("""
    SELECT songs.* FROM history
    JOIN songs ON history.song_id = songs.id
    WHERE history.username=?
    ORDER BY history.played_at DESC
    """, (session["user"],))
    data = cur.fetchall()
    con.close()
    return render_template_string(LIST_HTML, title="Recently Played", data=data, q="", mood="")

@app.route("/admin")
@admin_required
def admin():
    con = db()
    cur = con.cursor()
    cur.execute("SELECT * FROM songs ORDER BY id DESC")
    songs = cur.fetchall()
    con.close()
    return render_template_string(ADMIN_HTML, songs=songs, q="", mood="")

@app.route("/admin/add-song", methods=["POST"])
@admin_required
def admin_add_song():
    title = request.form["title"].strip()
    artist = request.form["artist"].strip()
    mood = request.form["mood"].strip()

    songfile = request.files.get("songfile")
    coverfile = request.files.get("coverfile")

    if not songfile or not songfile.filename:
        flash("Song file required.")
        return redirect("/admin")

    if not allowed_file(songfile.filename, ALLOWED_AUDIO):
        flash("Only mp3, wav, ogg, m4a audio allowed.")
        return redirect("/admin")

    safe_song = secure_filename(songfile.filename)
    song_name = str(int(time.time())) + "_" + safe_song
    songfile.save(os.path.join(SONG_FOLDER, song_name))

    cover_name = ""
    if coverfile and coverfile.filename:
        if allowed_file(coverfile.filename, ALLOWED_IMAGE):
            safe_cover = secure_filename(coverfile.filename)
            cover_name = str(int(time.time())) + "_" + safe_cover
            coverfile.save(os.path.join(COVER_FOLDER, cover_name))

    con = db()
    cur = con.cursor()
    cur.execute("""
    INSERT INTO songs(title, artist, mood, filename, cover)
    VALUES(?,?,?,?,?)
    """, (title, artist, mood, song_name, cover_name))
    con.commit()
    con.close()

    flash("Song uploaded successfully.")
    return redirect("/admin")

@app.route("/admin/delete/<int:song_id>")
@admin_required
def admin_delete(song_id):
    con = db()
    cur = con.cursor()
    cur.execute("SELECT filename, cover FROM songs WHERE id=?", (song_id,))
    song = cur.fetchone()

    if song:
        song_path = os.path.join(SONG_FOLDER, song["filename"])
        if os.path.exists(song_path):
            os.remove(song_path)

        if song["cover"]:
            cover_path = os.path.join(COVER_FOLDER, song["cover"])
            if os.path.exists(cover_path):
                os.remove(cover_path)

    cur.execute("DELETE FROM likes WHERE song_id=?", (song_id,))
    cur.execute("DELETE FROM history WHERE song_id=?", (song_id,))
    cur.execute("DELETE FROM songs WHERE id=?", (song_id,))
    con.commit()
    con.close()

    flash("Song deleted.")
    return redirect("/admin")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    print("Smartify Developer-Customer App Running")
    print("Local URL: http://127.0.0.1:8000")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=False)


