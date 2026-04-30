import os
import sqlite3
import requests
from urllib.parse import quote_plus
from functools import wraps
from datetime import timedelta
from flask import Flask, render_template_string, request, redirect, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ashplex_secret")
app.permanent_session_lifetime = timedelta(days=30)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ashplex_users.db")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "ashutosh")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Ashplex@123")

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
        username TEXT UNIQUE,
        password TEXT,
        role TEXT DEFAULT 'customer'
    )
    """)
    cur.execute("SELECT * FROM users WHERE username=?", (ADMIN_USERNAME,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users(username,password,role) VALUES(?,?,?)",
            (ADMIN_USERNAME, ADMIN_PASSWORD, "developer")
        )
    con.commit()
    con.close()

init_db()

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect("/")
        return f(*args, **kwargs)
    return wrapper

def developer_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect("/")
        if session.get("role") != "developer":
            return redirect("/home")
        return f(*args, **kwargs)
    return wrapper

def get_online_songs(query="arijit"):
    try:
        url = f"https://api.deezer.com/search?q={query}"
        data = requests.get(url, timeout=10).json()
        songs = []
        for s in data.get("data", [])[:18]:
            songs.append({
                "title": s.get("title", "Unknown"),
                "artist": s.get("artist", {}).get("name", "Unknown"),
                "cover": s.get("album", {}).get("cover_xl")
                         or s.get("album", {}).get("cover_big")
                         or s.get("album", {}).get("cover_medium", ""),
                "preview": s.get("preview", ""),
                "youtube": youtube_search_url(
                    s.get("title", "Unknown"),
                    s.get("artist", {}).get("name", "Unknown")
                )
            })
        return songs
    except Exception:
        return []

def ai_mood_query(mood="trending", level="medium"):
    mood = (mood or "trending").lower()
    level = (level or "medium").lower()

    mood_map = {
        "happy": {
            "low": "happy acoustic chill",
            "medium": "happy bollywood hits",
            "high": "party dance energetic"
        },
        "sad": {
            "low": "soft sad acoustic",
            "medium": "sad hindi songs",
            "high": "heartbreak emotional songs"
        },
        "romantic": {
            "low": "soft romantic",
            "medium": "romantic bollywood",
            "high": "love songs passionate"
        },
        "focus": {
            "low": "calm piano focus",
            "medium": "lofi focus beats",
            "high": "deep focus electronic"
        },
        "relax": {
            "low": "meditation calm music",
            "medium": "relaxing chill songs",
            "high": "chill house lounge"
        },
        "workout": {
            "low": "warmup workout songs",
            "medium": "gym workout music",
            "high": "high energy workout"
        },
        "angry": {
            "low": "dark chill music",
            "medium": "rock intense songs",
            "high": "aggressive workout music"
        },
        "trending": {
            "low": "acoustic hits",
            "medium": "arijit",
            "high": "trending dance hits"
        }
    }

    return mood_map.get(mood, mood_map["trending"]).get(level, mood_map["trending"]["medium"])



def youtube_search_url(title, artist):
    search_text = f"{title} {artist} song"
    return "https://www.youtube.com/results?search_query=" + quote_plus(search_text)

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>ASHPLEX Login</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
*{box-sizing:border-box}
body{margin:0;min-height:100vh;background:radial-gradient(circle at top,#3a1d2f,#08080b 48%,#000);color:white;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;display:flex;align-items:center;justify-content:center}
.login-card{width:360px;padding:34px;border-radius:28px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.12);backdrop-filter:blur(28px);box-shadow:0 30px 80px rgba(0,0,0,.45);text-align:center}
.logo{font-size:36px;font-weight:800;letter-spacing:.5px;margin-bottom:4px}
.tagline{color:#b8b8c6;font-size:13px;margin-bottom:28px}
input{width:100%;padding:14px 16px;margin:8px 0;border-radius:16px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.08);color:white;outline:none}
button{width:100%;padding:14px;margin-top:14px;border:0;border-radius:18px;color:white;font-weight:700;background:#fa233b;cursor:pointer}
.small{color:#8f8f9d;font-size:12px;margin-top:14px}
</style>
</head>
<body>
<div class="login-card">
  <div class="logo">🎧 ASHPLEX</div>
  <div class="tagline">Your Mood. Your Music. Your World.</div>
  <form method="POST" action="/login">
    <input name="user" placeholder="Username" required>
    <input name="password" type="password" placeholder="Password" required>
    <label style="display:flex;gap:8px;align-items:center;justify-content:center;color:#aaa;font-size:13px;margin-top:6px">
      <input type="checkbox" name="remember" checked style="width:auto;margin:0"> Remember me
    </label>
    <button>Enter ASHPLEX</button>
  </form>
  <div class="small">
    Developer: ashutosh / Ashplex@123<br>
    New customer? <a href="/register" style="color:#ff8a98">Create account</a>
  </div>
</div>
</body>
</html>
"""


REGISTER_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>ASHPLEX Register</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
*{box-sizing:border-box}
body{margin:0;min-height:100vh;background:radial-gradient(circle at top,#3a1d2f,#08080b 48%,#000);color:white;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;display:flex;align-items:center;justify-content:center}
.login-card{width:360px;padding:34px;border-radius:28px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.12);backdrop-filter:blur(28px);box-shadow:0 30px 80px rgba(0,0,0,.45);text-align:center}
.logo{font-size:36px;font-weight:800;letter-spacing:.5px;margin-bottom:4px}.tagline{color:#b8b8c6;font-size:13px;margin-bottom:28px}
input{width:100%;padding:14px 16px;margin:8px 0;border-radius:16px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.08);color:white;outline:none}
button{width:100%;padding:14px;margin-top:14px;border:0;border-radius:18px;color:white;font-weight:700;background:#fa233b;cursor:pointer}
.small{color:#8f8f9d;font-size:12px;margin-top:14px}a{color:#ff8a98}
</style>
</head>
<body>
<div class="login-card">
  <div class="logo">🎧 ASHPLEX</div>
  <div class="tagline">Customer Registration</div>
  <form method="POST" action="/register">
    <input name="user" placeholder="Create username" required>
    <input name="password" type="password" placeholder="Create password" required>
    <button>Create Customer Account</button>
  </form>
  <div class="small">Already have account? <a href="/">Login</a></div>
</div>
</body>
</html>
"""

APPLE_UI = """
<!DOCTYPE html>
<html>
<head>
<title>ASHPLEX</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#08080b;--panel:#121217;--panel2:#1c1c22;--text:#f5f5f7;--muted:#9898a6;--red:#fa233b;--red2:#ff5a6d}
body{min-height:100vh;background:linear-gradient(180deg,#181820 0%,#08080b 42%,#000 100%);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;overflow:hidden}
.app{width:100vw;height:100vh;display:grid;grid-template-columns:250px 1fr;grid-template-rows:1fr 92px;background:var(--bg)}
.sidebar{grid-row:1/2;background:rgba(18,18,23,.96);border-right:1px solid rgba(255,255,255,.08);padding:24px 18px;overflow:hidden}
.brand{display:flex;align-items:center;gap:10px;margin-bottom:28px}
.brand-icon{width:42px;height:42px;border-radius:14px;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,var(--red),#ff7b91);box-shadow:0 12px 35px rgba(250,35,59,.35);font-size:21px}
.brand-text h2{font-size:20px;letter-spacing:.3px}.brand-text p{font-size:11px;color:var(--muted)}
.nav-title{color:#777785;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1.2px;margin:20px 10px 8px}
.nav a{display:flex;align-items:center;gap:12px;padding:11px 12px;color:#c9c9d3;text-decoration:none;border-radius:12px;font-size:15px;margin:3px 0}
.nav a:hover,.nav a.active{background:rgba(255,255,255,.08);color:white}.nav a.active span:first-child{color:var(--red)}
.main{overflow-y:auto;padding:26px 34px 120px;background:radial-gradient(circle at 75% -10%, rgba(250,35,59,.20), transparent 32%),radial-gradient(circle at 25% 0%, rgba(255,255,255,.08), transparent 28%),linear-gradient(180deg,#181820,#09090d 45%,#000)}
.main::-webkit-scrollbar{width:7px}.main::-webkit-scrollbar-thumb{background:#2a2a32;border-radius:20px}
.topbar{display:flex;justify-content:space-between;align-items:center;gap:18px;margin-bottom:28px}
.search{flex:1;max-width:520px;position:relative}.search input{width:100%;padding:14px 18px 14px 44px;border:0;outline:none;border-radius:18px;color:white;background:rgba(255,255,255,.10);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,.10)}
.search-icon{position:absolute;top:13px;left:17px;color:#aaa}.user-pill{padding:11px 16px;border-radius:18px;background:rgba(255,255,255,.08);color:#ddd;font-size:14px}
.hero{display:grid;grid-template-columns:250px 1fr;gap:30px;align-items:end;min-height:300px;padding:28px;border-radius:34px;background:linear-gradient(135deg,rgba(255,255,255,.14),rgba(255,255,255,.04)),radial-gradient(circle at top right,rgba(250,35,59,.42),transparent 40%);border:1px solid rgba(255,255,255,.12);box-shadow:0 28px 90px rgba(0,0,0,.35);margin-bottom:32px}
.hero-cover{width:250px;height:250px;border-radius:30px;overflow:hidden;box-shadow:0 25px 70px rgba(0,0,0,.55);background:#222}.hero-cover img{width:100%;height:100%;object-fit:cover}
.hero-info .eyebrow{color:var(--red2);text-transform:uppercase;font-size:12px;font-weight:800;letter-spacing:1.6px;margin-bottom:10px}
.hero-info h1{font-size:64px;line-height:.95;letter-spacing:-2px;margin-bottom:12px}.hero-info p{color:#d5d5df;font-size:16px;margin-bottom:22px}
.hero-actions{display:flex;gap:12px;flex-wrap:wrap}.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;border:0;text-decoration:none;color:white;font-weight:750;padding:13px 22px;border-radius:999px;background:var(--red);cursor:pointer}.btn.secondary{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.12)}
.yt-btn{display:inline-flex;margin-top:10px;padding:9px 13px;border-radius:999px;background:#ff0033;color:white;text-decoration:none;font-weight:700;font-size:12px;align-items:center;gap:6px;box-shadow:0 10px 25px rgba(255,0,51,.22)}
.yt-btn:hover{filter:brightness(1.12)}
.section-row{display:flex;align-items:center;justify-content:space-between;margin:10px 0 16px}.section-row h2{font-size:26px;letter-spacing:-.5px}.section-row span{color:var(--muted)}
.mood-row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:24px}.mood{padding:10px 16px;border-radius:999px;background:rgba(255,255,255,.08);color:#d8d8e2;text-decoration:none;border:1px solid rgba(255,255,255,.08)}.mood:hover,.mood.active{background:rgba(250,35,59,.20);color:white;border-color:rgba(250,35,59,.35)}
.mood-ai-box{margin:0 0 24px;padding:18px;border-radius:24px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.10);backdrop-filter:blur(20px)}
.mood-ai-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:14px}
.mood-ai-head h3{font-size:18px}
.ai-badge{font-size:12px;color:#ffb3bd;background:rgba(250,35,59,.16);padding:7px 11px;border-radius:999px}
.mood-ai-form{display:grid;grid-template-columns:1fr 1fr auto;gap:12px;align-items:end}
.mood-ai-form label{display:block;color:var(--muted);font-size:12px;margin-bottom:6px}
.mood-ai-form select{width:100%;padding:13px 14px;border:0;outline:none;border-radius:16px;color:white;background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.10)}
.ai-result{margin-top:12px;color:#cfcfd8;font-size:13px}
.ai-dot{display:inline-block;width:8px;height:8px;background:#fa233b;border-radius:50%;margin-right:8px;box-shadow:0 0 18px #fa233b}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(165px,1fr));gap:20px}.card{background:rgba(255,255,255,.065);border:1px solid rgba(255,255,255,.08);border-radius:22px;padding:14px;transition:.25s ease;cursor:pointer}.card:hover{transform:translateY(-7px);background:rgba(255,255,255,.10);box-shadow:0 22px 55px rgba(0,0,0,.35)}
.card-cover{width:100%;aspect-ratio:1/1;border-radius:18px;overflow:hidden;background:#222;margin-bottom:12px;position:relative}.card-cover img{width:100%;height:100%;object-fit:cover}.play-badge{position:absolute;right:10px;bottom:10px;width:42px;height:42px;border-radius:50%;background:var(--red);display:flex;align-items:center;justify-content:center;opacity:0;transform:scale(.85);transition:.2s}.card:hover .play-badge{opacity:1;transform:scale(1)}
.card h3{font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:5px}.card p{color:var(--muted);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.player{grid-column:1/3;background:rgba(12,12,16,.92);backdrop-filter:blur(28px);border-top:1px solid rgba(255,255,255,.10);display:grid;grid-template-columns:320px 1fr 260px;align-items:center;padding:14px 28px;z-index:20}
.now{display:flex;align-items:center;gap:14px;min-width:0}.now-cover{width:60px;height:60px;border-radius:14px;overflow:hidden;background:#222}.now-cover img{width:100%;height:100%;object-fit:cover}.now h3{font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.now p{color:var(--muted);font-size:12px}
.controls{display:flex;align-items:center;justify-content:center;gap:18px}.control{border:0;color:white;background:transparent;font-size:22px;cursor:pointer}.play{width:46px;height:46px;border-radius:50%;background:white;color:#000;display:flex;align-items:center;justify-content:center;font-size:18px}.volume{justify-self:end;color:#aaa}.hidden-audio{display:none}
@media(max-width:850px){
body{overflow:auto}.app{display:block;min-height:100vh;height:auto;padding-bottom:92px}.sidebar{display:none}.main{padding:18px 16px 120px;min-height:100vh}.topbar{display:block}.search{max-width:none;margin-bottom:14px}.user-pill{display:inline-block}.hero{display:block;padding:20px;border-radius:28px;min-height:auto}.hero-cover{width:100%;height:auto;aspect-ratio:1/1;max-width:330px;margin:0 auto 22px}.hero-info{text-align:center}.hero-info h1{font-size:46px}.hero-actions{justify-content:center}.grid{grid-template-columns:1fr;gap:14px}.card{display:grid;grid-template-columns:86px 1fr;gap:14px;align-items:center;border-radius:20px}.card-cover{margin:0;border-radius:16px}.player{position:fixed;left:0;right:0;bottom:0;grid-template-columns:1fr auto;padding:12px 16px}.controls{justify-content:flex-end}.controls .control:not(.play),.volume{display:none}
.mood-ai-form{grid-template-columns:1fr}.mood-ai-head{display:block}.ai-badge{display:inline-block;margin-top:8px}
}
</style>
</head>
<body>
<div class="app">
  <aside class="sidebar">
    <div class="brand"><div class="brand-icon">🎧</div><div class="brand-text"><h2>ASHPLEX</h2><p>Your Mood. Your Music. Your World.</p></div></div>
    <nav class="nav">
      <div class="nav-title">Library</div>
      <a class="active" href="/home"><span>⌂</span> Listen Now</a>
      {% if role == 'developer' %}<a href="/developer"><span>⚙</span> Developer Panel</a>{% endif %}
      <a href="/home?q=arijit"><span>♪</span> Browse</a>
      <a href="/home?q=lofi"><span>◎</span> Radio</a>
      <a href="/home?q=love"><span>♥</span> Favourites</a>
      <div class="nav-title">Mood Playlist</div>
      <a href="/home?q=happy"><span>☀</span> Happy</a>
      <a href="/home?q=romantic"><span>❤</span> Romantic</a>
      <a href="/home?q=focus"><span>◉</span> Focus</a>
      <a href="/home?q=relax"><span>☾</span> Relax</a>
      <a href="/account"><span>⚙</span> Account</a>
      <a href="/logout"><span>⇥</span> Logout</a>
    </nav>
  </aside>

  <main class="main">
    <div class="topbar">
      <form class="search" action="/home"><span class="search-icon">⌕</span><input name="q" value="{{query}}" placeholder="Search songs, artists, moods..."></form>
      <div class="user-pill">Hi, {{user}} · {{role}}</div>
    </div>

    <section class="hero">
      <div class="hero-cover">{% if songs %}<img src="{{songs[0].cover}}">{% else %}<div style="height:100%;display:flex;align-items:center;justify-content:center;font-size:50px">🎧</div>{% endif %}</div>
      <div class="hero-info">
        <div class="eyebrow">ASHPLEX Mood Station</div>
        <h1>Your Mood.<br>Your Music.</h1>
        <p>Clean Apple Music style interface with Deezer preview + YouTube full song option. No manual upload needed.</p>
        <div class="hero-actions"><a class="btn" href="/home?q={{query}}">▶ Play Mix</a><a class="btn secondary" href="/home?q=lofi">Lofi</a><a class="btn secondary" href="/home?q=workout">Workout</a></div>
      </div>
    </section>

    <div class="section-row"><h2>Made For You</h2><span>{{songs|length}} tracks · AI query: {{query}}</span></div>

    <div class="mood-ai-box">
      <div class="mood-ai-head">
        <h3>🤖 AI Mood Level Recommendation</h3>
        <div class="ai-badge">Mood + Intensity based search</div>
      </div>

      <form class="mood-ai-form" action="/home">
        <div>
          <label>Select Mood</label>
          <select name="mood">
            <option value="trending" {% if mood=='trending' %}selected{% endif %}>🔥 Trending</option>
            <option value="happy" {% if mood=='happy' %}selected{% endif %}>😊 Happy</option>
            <option value="sad" {% if mood=='sad' %}selected{% endif %}>😔 Sad</option>
            <option value="romantic" {% if mood=='romantic' %}selected{% endif %}>❤️ Romantic</option>
            <option value="focus" {% if mood=='focus' %}selected{% endif %}>🎯 Focus</option>
            <option value="relax" {% if mood=='relax' %}selected{% endif %}>🌿 Relax</option>
            <option value="workout" {% if mood=='workout' %}selected{% endif %}>💪 Workout</option>
            <option value="angry" {% if mood=='angry' %}selected{% endif %}>😡 Angry</option>
          </select>
        </div>

        <div>
          <label>Mood Level</label>
          <select name="level">
            <option value="low" {% if level=='low' %}selected{% endif %}>Low / Soft</option>
            <option value="medium" {% if level=='medium' %}selected{% endif %}>Medium / Balanced</option>
            <option value="high" {% if level=='high' %}selected{% endif %}>High / Intense</option>
          </select>
        </div>

        <button class="btn" type="submit">Generate Mix</button>
      </form>

      <div class="ai-result"><span class="ai-dot"></span>AI selected: <b>{{mood|capitalize}}</b> mood with <b>{{level}}</b> level.</div>
    </div>

    <div class="mood-row">
      <a class="mood active" href="/home?mood=trending&level=medium">Trending</a>
      <a class="mood" href="/home?mood=happy&level=high">Happy High</a>
      <a class="mood" href="/home?mood=romantic&level=medium">Romantic</a>
      <a class="mood" href="/home?mood=focus&level=medium">Focus</a>
      <a class="mood" href="/home?mood=relax&level=low">Relax Low</a>
      <a class="mood" href="/home?mood=workout&level=high">Workout High</a>
    </div>

    <div class="grid">
      {% for s in songs %}
      <div class="card" onclick="playSong('{{s.preview}}','{{s.title|e}}','{{s.artist|e}}','{{s.cover}}')">
        <div class="card-cover"><img src="{{s.cover}}"><div class="play-badge">▶</div></div>
        <div>
          <h3>{{s.title}}</h3>
          <p>{{s.artist}}</p>
          <a class="yt-btn" href="{{s.youtube}}" target="_blank" onclick="event.stopPropagation()">▶ YouTube Full Song</a>
        </div>
      </div>
      {% else %}
      <p style="color:#aaa">No songs found. Try another search.</p>
      {% endfor %}
    </div>
  </main>

  <footer class="player">
    <div class="now">
      <div class="now-cover" id="nowCover">{% if songs %}<img src="{{songs[0].cover}}">{% else %}🎧{% endif %}</div>
      <div style="min-width:0"><h3 id="nowTitle">{% if songs %}{{songs[0].title}}{% else %}No Song{% endif %}</h3><p id="nowArtist">{% if songs %}{{songs[0].artist}}{% else %}Search music{% endif %}</p></div>
    </div>
    <div class="controls"><button class="control">⏮</button><button class="control play" id="playBtn">▶</button><button class="control">⏭</button></div>
    <div class="volume">🔊 ━━━━━</div>
  </footer>
</div>

<audio id="audio" class="hidden-audio" {% if songs %}src="{{songs[0].preview}}"{% endif %}></audio>
<script>
const audio=document.getElementById("audio");const playBtn=document.getElementById("playBtn");
function playSong(src,title,artist,cover){if(!src){return;}audio.src=src;document.getElementById("nowTitle").innerText=title;document.getElementById("nowArtist").innerText=artist;document.getElementById("nowCover").innerHTML='<img src="'+cover+'">';audio.play();playBtn.innerText="⏸";}
playBtn.addEventListener("click",()=>{if(audio.paused){audio.play();playBtn.innerText="⏸";}else{audio.pause();playBtn.innerText="▶";}});
audio.addEventListener("ended",()=>{playBtn.innerText="▶";});
</script>
</body>
</html>
"""



ACCOUNT_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>ASHPLEX Account</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
*{box-sizing:border-box}
body{margin:0;min-height:100vh;background:radial-gradient(circle at top right,rgba(250,35,59,.22),transparent 35%),#08080b;color:white;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;display:flex;align-items:center;justify-content:center;padding:20px}
.card{width:460px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.12);border-radius:28px;padding:28px;box-shadow:0 25px 80px rgba(0,0,0,.4)}
h1{margin-bottom:8px}.muted{color:#aaa;margin-bottom:20px}
.row{padding:13px 0;border-bottom:1px solid rgba(255,255,255,.08);display:flex;justify-content:space-between}
.btn{display:inline-block;margin-top:18px;padding:12px 18px;border-radius:999px;background:#fa233b;color:white;text-decoration:none;border:0;font-weight:700;cursor:pointer}
.btn.secondary{background:rgba(255,255,255,.12)}
.btn.danger{background:#b00020}
form{margin-top:10px}
small{color:#aaa;display:block;margin-top:10px;line-height:1.5}
</style>
</head>
<body>
<div class="card">
  <h1>🎧 ASHPLEX Account</h1>
  <p class="muted">Your account is saved in database for future login.</p>

  <div class="row"><span>Username</span><b>{{user}}</b></div>
  <div class="row"><span>Role</span><b>{{role}}</b></div>

  <a class="btn secondary" href="/home">Back to App</a>
  <a class="btn secondary" href="/logout">Logout</a>

  {% if role != 'developer' %}
  <form method="POST" action="/forget-account" onsubmit="return confirm('Are you sure? Your account will be deleted permanently.')">
    <button class="btn danger">Forget / Delete My Account</button>
    <small>This option removes your username and password from ASHPLEX database. You can register again later.</small>
  </form>
  {% endif %}
</div>
</body>
</html>
"""

DEVELOPER_UI = """
<!DOCTYPE html>
<html>
<head>
<title>ASHPLEX Developer Panel</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
*{box-sizing:border-box}
body{margin:0;background:#08080b;color:white;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}
.page{min-height:100vh;padding:28px;background:radial-gradient(circle at top right,rgba(250,35,59,.22),transparent 35%),#08080b}
.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}
.brand h1{font-size:34px;margin:0}.brand p{color:#aaa;margin:5px 0 0}
.btn{background:#fa233b;color:white;text-decoration:none;padding:12px 18px;border-radius:999px;font-weight:700;border:0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:18px;margin-bottom:24px}
.card{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.10);border-radius:24px;padding:22px;box-shadow:0 20px 60px rgba(0,0,0,.25)}
.card h2{margin:0 0 8px}.num{font-size:42px;font-weight:800;color:#ff5a6d}
.panel{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.10);border-radius:24px;padding:22px}
table{width:100%;border-collapse:collapse;margin-top:14px}
td,th{padding:13px;border-bottom:1px solid rgba(255,255,255,.08);text-align:left}
th{color:#aaa;font-size:13px}
input{padding:12px;border-radius:14px;border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.08);color:white;width:100%;margin:8px 0}
.formrow{display:grid;grid-template-columns:1fr auto;gap:10px;align-items:end}
@media(max-width:700px){.header{display:block}.formrow{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="page">
  <div class="header">
    <div class="brand">
      <h1>🎧 ASHPLEX Developer Panel</h1>
      <p>Manage platform, view customers and test AI music search.</p>
    </div>
    <div>
      <a class="btn" href="/home">Open Customer App</a>
      <a class="btn" href="/logout">Logout</a>
    </div>
  </div>

  <div class="grid">
    <div class="card"><h2>Total Users</h2><div class="num">{{total_users}}</div><p>Registered customers + developer</p></div>
    <div class="card"><h2>Customers</h2><div class="num">{{customers}}</div><p>People who can use ASHPLEX</p></div>
    <div class="card"><h2>AI Music Source</h2><div class="num">2</div><p>Deezer preview + YouTube full song</p></div>
  </div>

  <div class="panel">
    <h2>AI Search Test</h2>
    <form class="formrow" action="/home">
      <input name="q" placeholder="Try: arijit, lofi, workout, romantic">
      <button class="btn">Test in App</button>
    </form>
  </div>

  <br>

  <div class="panel">
    <h2>Registered Users</h2>
    <table>
      <tr><th>ID</th><th>Username</th><th>Role</th></tr>
      {% for u in users %}
      <tr><td>{{u.id}}</td><td>{{u.username}}</td><td>{{u.role}}</td></tr>
      {% endfor %}
    </table>
  </div>
</div>
</body>
</html>
"""

@app.route("/")
def login():
    return LOGIN_HTML

@app.route("/login", methods=["POST"])
def do_login():
    username = request.form.get("user", "").strip()
    password = request.form.get("password", "").strip()

    con = db()
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = cur.fetchone()
    con.close()

    if not user:
        return LOGIN_HTML.replace("Use any username to continue", "Wrong username or password")

    session["user"] = user["username"]
    session["role"] = user["role"]
    if request.form.get("remember"):
        session.permanent = True

    if user["role"] == "developer":
        return redirect("/developer")
    return redirect("/home")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return REGISTER_HTML

    username = request.form.get("user", "").strip()
    password = request.form.get("password", "").strip()

    try:
        con = db()
        cur = con.cursor()
        cur.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)", (username, password, "customer"))
        con.commit()
        con.close()
        return redirect("/")
    except sqlite3.IntegrityError:
        return REGISTER_HTML.replace("Customer Registration", "Username already exists")

@app.route("/home")
@login_required
def home():
    mood = request.args.get("mood", "trending")
    level = request.args.get("level", "medium")
    query = request.args.get("q")

    if not query:
        query = ai_mood_query(mood, level)

    songs = get_online_songs(query)
    return render_template_string(
        APPLE_UI,
        songs=songs,
        query=query,
        mood=mood,
        level=level,
        user=session.get("user", "guest"),
        role=session.get("role", "customer")
    )



@app.route("/account")
@login_required
def account():
    return render_template_string(
        ACCOUNT_HTML,
        user=session.get("user", "guest"),
        role=session.get("role", "customer")
    )

@app.route("/forget-account", methods=["POST"])
@login_required
def forget_account():
    if session.get("role") == "developer":
        return redirect("/account")

    username = session.get("user")

    con = db()
    cur = con.cursor()
    cur.execute("DELETE FROM users WHERE username=? AND role='customer'", (username,))
    con.commit()
    con.close()

    session.clear()
    return redirect("/")

@app.route("/developer")
@developer_required
def developer():
    con = db()
    cur = con.cursor()
    cur.execute("SELECT id, username, role FROM users ORDER BY id DESC")
    users = cur.fetchall()
    cur.execute("SELECT COUNT(*) AS c FROM users")
    total_users = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) AS c FROM users WHERE role='customer'")
    customers = cur.fetchone()["c"]
    con.close()

    return render_template_string(
        DEVELOPER_UI,
        users=users,
        total_users=total_users,
        customers=customers
    )

@app.route("/online")
@login_required
def online():
    return redirect("/home")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
