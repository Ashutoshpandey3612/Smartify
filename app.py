import os
import sqlite3
import requests
from functools import wraps
from datetime import timedelta, date
from urllib.parse import quote_plus
from flask import Flask, render_template_string, request, redirect, session, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ashplex_secret")
app.permanent_session_lifetime = timedelta(days=30)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ashplex_users.db")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "ashutosh")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Ashplex@123")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_stats(
        username TEXT PRIMARY KEY,
        total_plays INTEGER DEFAULT 0,
        today_plays INTEGER DEFAULT 0,
        total_rewards INTEGER DEFAULT 0,
        last_reward_date TEXT DEFAULT '',
        last_play_date TEXT DEFAULT ''
    )
    """)

    cur.execute("SELECT * FROM users WHERE role='developer'")
    dev = cur.fetchone()

    if not dev:
        cur.execute(
            "INSERT INTO users(username,password,role) VALUES(?,?,?)",
            (ADMIN_USERNAME, ADMIN_PASSWORD, "developer")
        )
    else:
        # Keep developer login updated with current code credentials
        cur.execute(
            "UPDATE users SET username=?, password=? WHERE role='developer'",
            (ADMIN_USERNAME, ADMIN_PASSWORD)
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

def youtube_search_url(title="", artist="", query=""):
    if query:
        search_text = query + " song"
    else:
        search_text = f"{title} {artist} song"
    return "https://www.youtube.com/results?search_query=" + quote_plus(search_text)

def youtube_embed_url(query=""):
    return "https://www.youtube.com/embed?listType=search&list=" + quote_plus(query + " song")

def get_youtube_video(query="arijit song"):
    """
    Uses official YouTube Data API v3 to get exact videoId.
    This fixes 'This video is unavailable' caused by search-list iframe embed.
    """
    if not YOUTUBE_API_KEY:
        return {
            "ok": False,
            "error": "YOUTUBE_API_KEY missing",
            "video_id": "",
            "title": "",
            "channel": "",
            "embed_url": "",
            "watch_url": youtube_search_url(query=query)
        }

    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": query + " song",
            "type": "video",
            "maxResults": 1,
            "videoEmbeddable": "true",
            "safeSearch": "none",
            "key": YOUTUBE_API_KEY
        }

        data = requests.get(url, params=params, timeout=10).json()

        items = data.get("items", [])
        if not items:
            return {
                "ok": False,
                "error": "No embeddable video found",
                "video_id": "",
                "title": "",
                "channel": "",
                "embed_url": "",
                "watch_url": youtube_search_url(query=query)
            }

        item = items[0]
        video_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        channel = item["snippet"]["channelTitle"]

        return {
            "ok": True,
            "error": "",
            "video_id": video_id,
            "title": title,
            "channel": channel,
            "embed_url": f"https://www.youtube.com/embed/{video_id}?autoplay=1&rel=0",
            "watch_url": f"https://www.youtube.com/watch?v={video_id}"
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "video_id": "",
            "title": "",
            "channel": "",
            "embed_url": "",
            "watch_url": youtube_search_url(query=query)
        }

def get_deezer_songs(query="arijit"):
    try:
        url = f"https://api.deezer.com/search?q={quote_plus(query)}"
        data = requests.get(url, timeout=10).json()

        songs = []
        for s in data.get("data", [])[:18]:
            title = s.get("title", "Unknown")
            artist = s.get("artist", {}).get("name", "Unknown")
            cover = (
                s.get("album", {}).get("cover_xl")
                or s.get("album", {}).get("cover_big")
                or s.get("album", {}).get("cover_medium", "")
            )

            songs.append({
                "id": s.get("id"),
                "title": title,
                "artist": artist,
                "cover": cover,
                "preview": s.get("preview", ""),
                "youtube_url": youtube_search_url(title, artist),
                "source": "Deezer + YouTube"
            })
        return songs
    except Exception:
        return []

def update_user_activity(username):
    today = str(date.today())

    con = db()
    cur = con.cursor()
    cur.execute("SELECT * FROM user_stats WHERE username=?", (username,))
    stat = cur.fetchone()

    reward_added = 0

    if not stat:
        cur.execute("""
            INSERT INTO user_stats(username, total_plays, today_plays, total_rewards, last_reward_date, last_play_date)
            VALUES(?,?,?,?,?,?)
        """, (username, 1, 1, 0, "", today))
        today_plays = 1
        total_rewards = 0
    else:
        if stat["last_play_date"] == today:
            today_plays = stat["today_plays"] + 1
        else:
            today_plays = 1

        total_rewards = stat["total_rewards"]

        if today_plays >= 20 and stat["last_reward_date"] != today:
            reward_added = 10
            total_rewards += 10
            cur.execute("""
                UPDATE user_stats
                SET total_plays = total_plays + 1,
                    today_plays = ?,
                    total_rewards = ?,
                    last_reward_date = ?,
                    last_play_date = ?
                WHERE username=?
            """, (today_plays, total_rewards, today, today, username))
        else:
            cur.execute("""
                UPDATE user_stats
                SET total_plays = total_plays + 1,
                    today_plays = ?,
                    total_rewards = ?,
                    last_play_date = ?
                WHERE username=?
            """, (today_plays, total_rewards, today, username))

    con.commit()
    con.close()

    return {
        "today_plays": today_plays,
        "total_rewards": total_rewards,
        "reward_added": reward_added,
        "target": 20,
        "target_achieved": today_plays >= 20
    }

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>ASHPLEX Login</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
*{box-sizing:border-box}
body{margin:0;min-height:100vh;background:radial-gradient(circle at top,#3a1d2f,#08080b 48%,#000);color:white;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;display:flex;align-items:center;justify-content:center}
.card{width:370px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.12);border-radius:28px;padding:34px;text-align:center;box-shadow:0 30px 90px rgba(0,0,0,.45)}
h1{font-size:36px;margin:0 0 4px}.tag{color:#b8b8c6;font-size:13px;margin-bottom:24px}
input{width:100%;padding:14px;margin:8px 0;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.08);border-radius:16px;color:white}
button{width:100%;padding:14px;margin-top:12px;border:0;background:#fa233b;color:white;border-radius:18px;font-weight:800;cursor:pointer}
a{color:#ff8a98}.small{font-size:12px;color:#aaa;margin-top:14px;line-height:1.6}
</style>
</head>
<body>
<div class="card">
<h1>🎧 ASHPLEX</h1>
<div class="tag">Your Mood. Your Music. Your World.</div>
<form method="POST" action="/login">
<input name="user" placeholder="Username" required>
<input name="password" type="password" placeholder="Password" required>
<label style="display:flex;gap:8px;align-items:center;justify-content:center;color:#aaa;font-size:13px;margin-top:8px">
<input type="checkbox" name="remember" checked style="width:auto;margin:0"> Remember me
</label>
<button>Login</button>
</form>
<div class="small">
Developer: ashutosh / Ashplex@123<br>
New customer? <a href="/register">Create account</a>
</div>
</div>

<script>
document.querySelectorAll(".player-info h2").forEach(el=>{
  const txt=document.createElement("textarea");
  txt.innerHTML=el.innerHTML;
  el.innerText=txt.value;
});
</script>
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
.card{width:370px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.12);border-radius:28px;padding:34px;text-align:center;box-shadow:0 30px 90px rgba(0,0,0,.45)}
h1{font-size:36px;margin:0 0 4px}.tag{color:#b8b8c6;font-size:13px;margin-bottom:24px}
input{width:100%;padding:14px;margin:8px 0;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.08);border-radius:16px;color:white}
button{width:100%;padding:14px;margin-top:12px;border:0;background:#fa233b;color:white;border-radius:18px;font-weight:800;cursor:pointer}
a{color:#ff8a98}.small{font-size:12px;color:#aaa;margin-top:14px}
</style>
</head>
<body>
<div class="card">
<h1>🎧 ASHPLEX</h1>
<div class="tag">Customer Registration</div>
<form method="POST" action="/register">
<input name="user" placeholder="Create username" required>
<input name="password" type="password" placeholder="Create password" required>
<button>Create Account</button>
</form>
<div class="small">Already have account? <a href="/">Login</a></div>
</div>

<script>
document.querySelectorAll(".player-info h2").forEach(el=>{
  const txt=document.createElement("textarea");
  txt.innerHTML=el.innerHTML;
  el.innerText=txt.value;
});
</script>
</body>
</html>
"""

APP_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>ASHPLEX</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#08080b;--text:#f5f5f7;--muted:#9898a6;--red:#fa233b;--red2:#ff5a6d}
body{min-height:100vh;background:#08080b;color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;overflow:hidden}
.app{width:100vw;height:100vh;display:grid;grid-template-columns:250px 1fr;grid-template-rows:1fr 92px;background:#08080b}
.sidebar{grid-row:1/2;background:rgba(18,18,23,.96);border-right:1px solid rgba(255,255,255,.08);padding:24px 18px}
.brand{display:flex;align-items:center;gap:10px;margin-bottom:28px}.brand-icon{width:42px;height:42px;border-radius:14px;background:linear-gradient(135deg,var(--red),#ff7b91);display:flex;align-items:center;justify-content:center;font-size:21px}.brand h2{font-size:20px}.brand p{font-size:11px;color:var(--muted)}
.nav-title{color:#777785;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1.2px;margin:20px 10px 8px}
.nav a{display:flex;align-items:center;gap:12px;padding:11px 12px;color:#c9c9d3;text-decoration:none;border-radius:12px;font-size:15px;margin:3px 0}.nav a:hover,.nav a.active{background:rgba(255,255,255,.08);color:white}
.main{overflow-y:auto;padding:26px 34px 120px;background:radial-gradient(circle at 75% -10%, rgba(250,35,59,.20), transparent 32%),linear-gradient(180deg,#181820,#09090d 45%,#000)}
.topbar{display:flex;justify-content:space-between;align-items:center;gap:18px;margin-bottom:28px}.search{flex:1;max-width:520px;position:relative}.search input{width:100%;padding:14px 18px;border:0;outline:none;border-radius:18px;color:white;background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.10)}.user-pill{padding:11px 16px;border-radius:18px;background:rgba(255,255,255,.08);color:#ddd;font-size:14px}
.hero{display:grid;grid-template-columns:250px 1fr;gap:30px;align-items:end;min-height:300px;padding:28px;border-radius:34px;background:linear-gradient(135deg,rgba(255,255,255,.14),rgba(255,255,255,.04)),radial-gradient(circle at top right,rgba(250,35,59,.42),transparent 40%);border:1px solid rgba(255,255,255,.12);box-shadow:0 28px 90px rgba(0,0,0,.35);margin-bottom:28px}.hero-cover{width:250px;height:250px;border-radius:30px;overflow:hidden;box-shadow:0 25px 70px rgba(0,0,0,.55);background:#222}.hero-cover img{width:100%;height:100%;object-fit:cover}.hero h1{font-size:64px;line-height:.95;letter-spacing:-2px;margin-bottom:12px}.hero p{color:#d5d5df;font-size:16px;margin-bottom:22px}.eyebrow{color:var(--red2);text-transform:uppercase;font-size:12px;font-weight:800;letter-spacing:1.6px;margin-bottom:10px}
.btn{display:inline-flex;align-items:center;justify-content:center;border:0;text-decoration:none;color:white;font-weight:750;padding:13px 22px;border-radius:999px;background:var(--red);cursor:pointer}.btn.secondary{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.12)}
.mood-ai-box{margin:0 0 24px;padding:18px;border-radius:24px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.10);backdrop-filter:blur(20px)}.mood-ai-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:14px}.mood-ai-head h3{font-size:18px}.ai-badge{font-size:12px;color:#ffb3bd;background:rgba(250,35,59,.16);padding:7px 11px;border-radius:999px}.mood-ai-form{display:grid;grid-template-columns:1fr 1fr auto;gap:12px;align-items:end}.mood-ai-form label{display:block;color:var(--muted);font-size:12px;margin-bottom:6px}.mood-ai-form select{width:100%;padding:13px 14px;border:0;outline:none;border-radius:16px;color:white;background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.10)}
.hybrid-box{margin:0 0 24px;padding:18px;border-radius:24px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.10)}.source-badge{display:inline-block;margin-top:8px;padding:6px 10px;border-radius:999px;background:rgba(250,35,59,.16);color:#ffb3bd;font-size:12px;text-decoration:none}
.section-row{display:flex;align-items:center;justify-content:space-between;margin:10px 0 16px}.section-row h2{font-size:26px}.section-row span{color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(165px,1fr));gap:20px}.card{background:rgba(255,255,255,.065);border:1px solid rgba(255,255,255,.08);border-radius:22px;padding:14px;transition:.25s;cursor:pointer}.card:hover{transform:translateY(-7px);background:rgba(255,255,255,.10);box-shadow:0 22px 55px rgba(0,0,0,.35)}.card-cover{width:100%;aspect-ratio:1/1;border-radius:18px;overflow:hidden;background:#222;margin-bottom:12px;position:relative}.card-cover img{width:100%;height:100%;object-fit:cover}.play-badge{position:absolute;right:10px;bottom:10px;width:42px;height:42px;border-radius:50%;background:var(--red);display:flex;align-items:center;justify-content:center;opacity:0;transition:.2s}.card:hover .play-badge{opacity:1}.card h3{font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:5px}.card p{color:var(--muted);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.yt-btn{display:inline-flex;margin-top:10px;padding:8px 11px;border-radius:999px;background:#ff0033;color:white;text-decoration:none;font-size:12px;font-weight:800}
.player{grid-column:1/3;background:rgba(12,12,16,.92);backdrop-filter:blur(28px);border-top:1px solid rgba(255,255,255,.10);display:grid;grid-template-columns:320px 1fr 260px;align-items:center;padding:14px 28px;z-index:20}.now{display:flex;align-items:center;gap:14px;min-width:0}.now-cover{width:60px;height:60px;border-radius:14px;overflow:hidden;background:#222}.now-cover img{width:100%;height:100%;object-fit:cover}.now h3{font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.now p{color:var(--muted);font-size:12px}.controls{display:flex;align-items:center;justify-content:center;gap:18px}.control{border:0;color:white;background:transparent;font-size:22px;cursor:pointer}.play{width:46px;height:46px;border-radius:50%;background:white;color:#000}.hidden-audio{display:none}.volume{justify-self:end;color:#aaa}
@media(max-width:850px){
body{overflow:auto;background:radial-gradient(circle at top,#302a33,#08080b 55%,#000)}
.app{display:block;min-height:100vh;height:auto;padding-bottom:92px}
.sidebar{display:none}
.main{padding:14px 14px 120px;min-height:100vh;background:radial-gradient(circle at top left,rgba(250,35,59,.20),transparent 35%),linear-gradient(180deg,#17171d,#07070a)}
.topbar{display:block;margin-bottom:16px}
.search{max-width:none;margin-bottom:12px}
.search input{border-radius:999px;padding:15px 18px}
.user-pill{display:inline-block;border-radius:999px}
.hero{display:block;padding:18px;border-radius:34px;min-height:auto;background:linear-gradient(180deg,rgba(255,255,255,.13),rgba(255,255,255,.05));box-shadow:0 22px 70px rgba(0,0,0,.45)}
.hero-cover{width:100%;height:auto;aspect-ratio:1/1;max-width:320px;margin:0 auto 22px;border-radius:32px}
.hero div:last-child{text-align:left}
.hero h1{font-size:38px;line-height:1.02;letter-spacing:-1px;text-align:left}
.hero p{font-size:14px;line-height:1.5}
.hero .btn{padding:12px 18px}
.mood-ai-box{border-radius:28px;padding:16px}
.mood-ai-form{grid-template-columns:1fr}
.hybrid-box{border-radius:28px}
.grid{grid-template-columns:1fr;gap:12px}
.card{display:grid;grid-template-columns:74px 1fr;gap:14px;align-items:center;border-radius:22px;padding:12px;background:rgba(255,255,255,.075)}
.card:hover{transform:none}
.card-cover{margin:0;border-radius:18px}
.play-badge{opacity:1;width:34px;height:34px}
.yt-btn{font-size:11px;padding:7px 10px}
.player{position:fixed;left:10px;right:10px;bottom:10px;grid-template-columns:1fr auto;height:72px;border-radius:24px;padding:10px 14px;box-shadow:0 20px 60px rgba(0,0,0,.55)}
.now-cover{width:52px;height:52px;border-radius:16px}
.controls{justify-content:flex-end}
.controls .control:not(.play),.volume{display:none}
.play{width:46px;height:46px}
}
</style>
</head>
<body>
<div class="app">
<aside class="sidebar">
<div class="brand"><div class="brand-icon">🎧</div><div><h2>ASHPLEX</h2><p>Your Mood. Your Music. Your World.</p></div></div>
<nav class="nav">
<div class="nav-title">Library</div>
<a class="active" href="/home"><span>⌂</span> Listen Now</a>
{% if role == 'developer' %}<a href="/developer"><span>⚙</span> Developer Panel</a>{% endif %}
<a href="/wallet"><span>🎁</span> Rewards</a>
<a href="/account"><span>⚙</span> Account</a>
<a href="/youtube?q={{query}}" ><span>▶</span> YouTube Full Mode</a>
<a href="/logout"><span>⇥</span> Logout</a>
</nav>
</aside>

<main class="main">
<div class="topbar">
<form class="search" action="/home"><input name="q" value="{{query}}" placeholder="Search Deezer preview songs..."></form>
<div class="user-pill">Hi, {{user}} · {{role}}</div>
</div>

<section class="hero">
<div class="hero-cover">{% if songs and songs[0].cover %}<img src="{{songs[0].cover}}">{% else %}<div style="height:100%;display:flex;align-items:center;justify-content:center;font-size:52px">🎧</div>{% endif %}</div>
<div>
<div class="eyebrow">ASHPLEX Hybrid Music</div>
<h1>Your Mood.<br>Your Music.</h1>
<p>Deezer API gives fast preview and metadata. YouTube gives full-song discovery.</p>
<a class="btn" href="/home">Play Mix</a>
<a class="btn secondary" href="/youtube?q={{query}}">YouTube Full Mode</a>
</div>
</section>

<div class="mood-ai-box">
<div class="mood-ai-head"><h3>🤖 AI Mood Level Recommendation</h3><div class="ai-badge">Mood + Level → Deezer search</div></div>
<form class="mood-ai-form" action="/home">
<div>
<label>Select Mood</label>
<select name="mood">
<option value="trending">Trending</option><option value="happy">Happy</option><option value="sad">Sad</option><option value="romantic">Romantic</option><option value="focus">Focus</option><option value="relax">Relax</option><option value="workout">Workout</option><option value="angry">Angry</option>
</select>
</div>
<div>
<label>Mood Level</label>
<select name="level">
<option value="low">Low / Soft</option><option value="medium" selected>Medium</option><option value="high">High / Intense</option>
</select>
</div>
<button class="btn" type="submit">Generate Mix</button>
</form>
</div>

<div class="hybrid-box">
<h3>🌐 Hybrid Full Song Source</h3>
<p style="color:#aaa;margin:8px 0 12px">Preview on ASHPLEX via Deezer. Full song option opens YouTube search/player.</p>
<a class="source-badge" href="/youtube?q={{query}}">Open YouTube Full Song Mode</a>
</div>

<div class="section-row"><h2>Made For You</h2><span>{{songs|length}} Deezer preview tracks · {{query}}</span></div>

<div class="grid">
{% for s in songs %}
<div class="card" onclick="playSong('{{s.preview}}','{{s.title|e}}','{{s.artist|e}}','{{s.cover}}')">
<div class="card-cover">{% if s.cover %}<img src="{{s.cover}}">{% else %}<div style="height:100%;display:flex;align-items:center;justify-content:center;font-size:35px">🎵</div>{% endif %}<div class="play-badge">▶</div></div>
<div><h3>{{s.title}}</h3><p>{{s.artist}}</p><a class="yt-btn" href="/youtube?q={{s.title}} {{s.artist}}" onclick="event.stopPropagation()">▶ Play Full in ASHPLEX</a></div>
</div>
{% else %}
<p style="color:#aaa">No songs found. Try another search.</p>
{% endfor %}
</div>
</main>

<footer class="player">
<div class="now">
<div class="now-cover" id="nowCover">{% if songs and songs[0].cover %}<img src="{{songs[0].cover}}">{% else %}🎧{% endif %}</div>
<div style="min-width:0"><h3 id="nowTitle">{% if songs %}{{songs[0].title}}{% else %}No Song{% endif %}</h3><p id="nowArtist">{% if songs %}{{songs[0].artist}}{% else %}Search music{% endif %}</p></div>
</div>
<div class="controls"><button class="control">⏮</button><button class="control play" id="playBtn">▶</button><button class="control">⏭</button></div>
<div class="volume">🔊 ━━━━━</div>
</footer>
</div>

<audio id="audio" class="hidden-audio" {% if songs %}src="{{songs[0].preview}}"{% endif %}></audio>
<script>
const audio=document.getElementById("audio");const playBtn=document.getElementById("playBtn");
function playSong(src,title,artist,cover){
  if(!src){alert("Preview not available. Use YouTube Full Song button.");return;}
  audio.src=src;
  document.getElementById("nowTitle").innerText=title;
  document.getElementById("nowArtist").innerText=artist;
  document.getElementById("nowCover").innerHTML=cover?'<img src="'+cover+'">':'🎵';
  audio.play();
  playBtn.innerText="⏸";
  fetch("/api/play").then(r=>r.json()).then(d=>{
    if(d.reward_added && d.reward_added > 0){
      alert("🎉 Congratulations! You earned ₹" + d.reward_added + " reward for completing daily target.");
    }
  });
}
playBtn.addEventListener("click",()=>{if(audio.paused){audio.play();playBtn.innerText="⏸";fetch("/api/play");}else{audio.pause();playBtn.innerText="▶"}});
audio.addEventListener("ended",()=>{playBtn.innerText="▶"});
</script>

<script>
document.querySelectorAll(".player-info h2").forEach(el=>{
  const txt=document.createElement("textarea");
  txt.innerHTML=el.innerHTML;
  el.innerText=txt.value;
});
</script>
</body>
</html>
"""

YOUTUBE_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>ASHPLEX Player</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{
  min-height:100vh;
  background:
    radial-gradient(circle at 25% 10%,rgba(250,35,59,.28),transparent 30%),
    radial-gradient(circle at 75% 5%,rgba(113,80,255,.20),transparent 28%),
    linear-gradient(180deg,#181820,#07070a 52%,#000);
  color:white;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;
}
.page{
  min-height:100vh;
  padding:26px;
}
.header{
  max-width:1180px;
  margin:0 auto 22px;
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:18px;
}
.logo h1{font-size:32px;letter-spacing:-.5px}
.logo p{color:#aaa;margin-top:6px}
.search{
  display:flex;
  gap:10px;
  width:min(560px,100%);
}
.search input{
  flex:1;
  padding:14px 18px;
  border-radius:999px;
  border:1px solid rgba(255,255,255,.12);
  background:rgba(255,255,255,.09);
  color:white;
  outline:none;
}
.btn{
  border:0;
  border-radius:999px;
  background:#fa233b;
  color:white;
  padding:13px 20px;
  font-weight:800;
  text-decoration:none;
  cursor:pointer;
  white-space:nowrap;
}
.player-card{
  max-width:1180px;
  margin:0 auto;
  border-radius:38px;
  overflow:hidden;
  background:linear-gradient(135deg,rgba(255,255,255,.15),rgba(255,255,255,.045));
  border:1px solid rgba(255,255,255,.12);
  box-shadow:0 35px 120px rgba(0,0,0,.58);
  position:relative;
}
.player-card:before{
  content:"";
  position:absolute;
  inset:-40%;
  background:
    radial-gradient(circle at 18% 15%,rgba(250,35,59,.35),transparent 24%),
    radial-gradient(circle at 82% 5%,rgba(120,90,255,.25),transparent 30%);
  filter:blur(18px);
  opacity:.7;
}
.player-layout{
  position:relative;
  display:grid;
  grid-template-columns:330px 1fr;
  gap:34px;
  align-items:center;
  padding:34px;
}
.video-box{
  width:330px;
  height:330px;
  border-radius:34px;
  overflow:hidden;
  background:#000;
  box-shadow:0 30px 80px rgba(0,0,0,.65);
  position:relative;
}
.video-box iframe{
  width:100%;
  height:100%;
  border:0;
  background:#000;
}
.video-box:after{
  content:"";
  position:absolute;
  left:32px;
  right:32px;
  bottom:-28px;
  height:60px;
  background:#fa233b;
  filter:blur(40px);
  opacity:.35;
}
.now-badge{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding:9px 14px;
  border-radius:999px;
  background:rgba(250,35,59,.16);
  border:1px solid rgba(250,35,59,.25);
  color:#ff9aaa;
  font-size:13px;
  font-weight:800;
  margin-bottom:18px;
}
.title{
  font-size:40px;
  line-height:1.12;
  letter-spacing:-1px;
  margin-bottom:10px;
}
.channel{
  color:#c5c5d0;
  font-size:16px;
  margin-bottom:24px;
}
.progress{
  display:grid;
  grid-template-columns:44px 1fr 48px;
  align-items:center;
  gap:12px;
  color:#cfcfd8;
  font-size:13px;
  margin:20px 0;
}
.bar{
  height:7px;
  border-radius:999px;
  background:rgba(255,255,255,.16);
  position:relative;
}
.bar:before{
  content:"";
  position:absolute;
  inset:0 auto 0 0;
  width:42%;
  border-radius:999px;
  background:#fff;
}
.bar:after{
  content:"";
  position:absolute;
  left:42%;
  top:50%;
  transform:translate(-50%,-50%);
  width:15px;
  height:15px;
  border-radius:50%;
  background:#fff;
  box-shadow:0 0 18px rgba(255,255,255,.45);
}
.controls{
  display:flex;
  justify-content:center;
  align-items:center;
  gap:26px;
  margin:24px 0;
}
.icon{
  font-size:24px;
  color:#f2f2f6;
  opacity:.9;
}
.pause{
  width:78px;
  height:78px;
  border-radius:50%;
  background:#fff;
  color:#111;
  display:flex;
  align-items:center;
  justify-content:center;
  font-size:38px;
  font-weight:900;
  box-shadow:0 18px 45px rgba(255,255,255,.18);
}
.actions{
  display:flex;
  gap:10px;
  flex-wrap:wrap;
  margin:22px 0;
}
.actions span{
  padding:9px 13px;
  border-radius:999px;
  background:rgba(255,255,255,.085);
  border:1px solid rgba(255,255,255,.10);
  color:#ddd;
  font-size:13px;
}
.lyrics{
  margin-top:22px;
  padding:18px;
  border-radius:26px;
  background:rgba(255,255,255,.075);
  border:1px solid rgba(255,255,255,.10);
  color:#cfcfd8;
  line-height:1.7;
}
.lyrics h3{
  text-align:center;
  margin-bottom:10px;
  color:white;
}
.api-warning{
  max-width:900px;
  margin:40px auto;
  padding:26px;
  border-radius:28px;
  background:rgba(255,255,255,.08);
  border:1px solid rgba(255,255,255,.12);
}
@media(max-width:850px){
  .page{padding:14px}
  .header{display:block}
  .logo{margin-bottom:16px}
  .logo h1{font-size:26px}
  .search{width:100%}
  .player-card{border-radius:34px;max-width:430px}
  .player-layout{display:block;padding:18px}
  .video-box{
    width:100%;
    height:auto;
    aspect-ratio:1/1;
    border-radius:30px;
    margin-bottom:22px;
  }
  .title{font-size:24px;line-height:1.18}
  .channel{font-size:14px}
  .progress{grid-template-columns:38px 1fr 42px}
  .controls{gap:22px}
  .pause{width:68px;height:68px;font-size:32px}
  .actions{justify-content:space-between}
  .lyrics{border-radius:24px}
}
</style>
</head>
<body>
<div class="page">
  <div class="header">
    <div class="logo">
      <h1>🎧 ASHPLEX Player</h1>
      <p>Your Mood. Your Music. Your World.</p>
    </div>
    <form class="search" action="/youtube">
      <input name="q" value="{{q}}" placeholder="Search full song...">
      <button class="btn">Search</button>
    </form>
    <a class="btn" href="/home">Back</a>
  </div>

  {% if video.ok %}
  <div class="player-card">
    <div class="player-layout">
      <div class="video-box">
        <iframe src="{{video.embed_url}}" allow="autoplay; encrypted-media" allowfullscreen></iframe>
      </div>

      <div>
        <div class="now-badge">🎵 Now Playing inside ASHPLEX</div>
        <h2 class="title">{{video.title}}</h2>
        <p class="channel">{{video.channel}}</p>

        <div class="progress">
          <span>0:00</span>
          <div class="bar"></div>
          <span>Full</span>
        </div>

        <div class="controls">
          <span class="icon">↝</span>
          <span class="icon">⏮</span>
          <div class="pause">Ⅱ</div>
          <span class="icon">⏭</span>
          <span class="icon">↻</span>
        </div>

        <div class="actions">
          <span>♡ Like</span>
          <span>☰ Queue</span>
          <span>↗ Share</span>
          <span>AI Mood</span>
        </div>

        <div class="lyrics">
          <h3>Lyrics</h3>
          <p>Music plays inside ASHPLEX with AI mood selection.<br>Your Mood. Your Music. Your World.</p>
        </div>
      </div>
    </div>
  </div>
  {% else %}
  <div class="api-warning">
    <h2>⚠️ YouTube API setup needed</h2>
    <p style="color:#aaa;margin:12px 0">{{video.error}}</p>
    <p style="color:#aaa">Add YOUTUBE_API_KEY in Render Environment Variables, then redeploy.</p>
    <br>
    <a class="btn" href="{{video.watch_url}}" target="_blank">Open fallback on YouTube</a>
  </div>
  {% endif %}
</div>

<script>
document.querySelectorAll(".title").forEach(el=>{
  const t=document.createElement("textarea");
  t.innerHTML=el.innerHTML;
  el.innerText=t.value;
});
</script>
</body>
</html>
"""


DEVELOPER_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>ASHPLEX Developer</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(circle at top right,rgba(250,35,59,.22),transparent 35%),#08080b;color:white;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}
.page{min-height:100vh;padding:28px}.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}.btn{background:#fa233b;color:white;text-decoration:none;padding:12px 18px;border-radius:999px;font-weight:700;border:0;cursor:pointer}.btn.secondary{background:rgba(255,255,255,.12)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:22px;margin-bottom:22px}.panel{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.10);border-radius:24px;padding:22px}.panel h2{margin-top:0}.big{font-size:42px;color:#ff8a98;font-weight:800}table{width:100%;border-collapse:collapse;margin-top:12px}td,th{padding:12px;border-bottom:1px solid rgba(255,255,255,.08);text-align:left}th{color:#aaa}
@media(max-width:850px){.header{display:block}}
</style>
</head>
<body>
<div class="page">
<div class="header">
<div><h1>🎧 ASHPLEX Developer Panel</h1><p style="color:#aaa">Deezer + YouTube hybrid platform with customer analytics.</p></div>
<div><a class="btn secondary" href="/home">Open App</a> <a class="btn secondary" href="/logout">Logout</a></div>
</div>

<div class="grid">
<div class="panel"><h2>Total Customers</h2><div class="big">{{customer_count}}</div><p style="color:#aaa">Registered customer accounts</p></div>
<div class="panel"><h2>Total Plays</h2><div class="big">{{total_plays}}</div><p style="color:#aaa">Customer preview play activity</p></div>
<div class="panel"><h2>Music Sources</h2><div class="big">2</div><p style="color:#aaa">Deezer preview + YouTube full song</p></div>
</div>

<div class="panel">
<h2>Customer Listening Activity & Reward Status</h2>
<p style="color:#aaa">Rule: If customer listens 20 songs in one day, reward target is achieved.</p>
<table>
<tr><th>Customer</th><th>Total Plays</th><th>Today Plays</th><th>Reward Earned</th><th>Status</th></tr>
{% for u in stats %}
<tr>
<td>{{u.username}}</td>
<td>{{u.total_plays}}</td>
<td>{{u.today_plays}}</td>
<td>₹{{u.total_rewards}}</td>
<td>{% if u.today_plays >= 20 %}🔥 Target Achieved{% else %}⏳ In Progress{% endif %}</td>
</tr>
{% else %}
<tr><td colspan="5" style="color:#aaa">No listening activity yet.</td></tr>
{% endfor %}
</table>
</div>
</div>

<script>
document.querySelectorAll(".player-info h2").forEach(el=>{
  const txt=document.createElement("textarea");
  txt.innerHTML=el.innerHTML;
  el.innerText=txt.value;
});
</script>
</body>
</html>
"""

ACCOUNT_HTML = """
<!DOCTYPE html>
<html>
<head><title>ASHPLEX Account</title><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>
body{margin:0;min-height:100vh;background:#08080b;color:white;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;display:flex;align-items:center;justify-content:center}.card{width:440px;background:rgba(255,255,255,.08);border-radius:24px;padding:28px}.btn{display:inline-block;margin-top:18px;padding:12px 18px;border-radius:999px;background:#fa233b;color:white;text-decoration:none;border:0;font-weight:700;cursor:pointer}.secondary{background:rgba(255,255,255,.12)}.danger{background:#b00020}.row{padding:12px 0;border-bottom:1px solid rgba(255,255,255,.08);display:flex;justify-content:space-between}</style></head>
<body><div class="card"><h1>🎧 ASHPLEX Account</h1><p style="color:#aaa">Your account is saved in database for future login.</p><div class="row"><span>Username</span><b>{{user}}</b></div><div class="row"><span>Role</span><b>{{role}}</b></div><a class="btn secondary" href="/home">Back</a> <a class="btn secondary" href="/logout">Logout</a>{% if role != 'developer' %}<form method="POST" action="/forget-account" onsubmit="return confirm('Delete account permanently?')"><button class="btn danger">Forget / Delete My Account</button></form>{% endif %}</div>
<script>
document.querySelectorAll(".player-info h2").forEach(el=>{
  const txt=document.createElement("textarea");
  txt.innerHTML=el.innerHTML;
  el.innerText=txt.value;
});
</script>
</body></html>
"""

WALLET_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>ASHPLEX Rewards</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body{margin:0;min-height:100vh;background:radial-gradient(circle at top right,rgba(250,35,59,.22),transparent 35%),#08080b;color:white;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;display:flex;align-items:center;justify-content:center;padding:20px}
.card{width:460px;background:rgba(255,255,255,.08);border-radius:24px;padding:28px;border:1px solid rgba(255,255,255,.12)}
h1{margin:0 0 10px}.big{font-size:48px;color:#ff8a98;font-weight:800}.muted{color:#aaa}.bar{height:12px;background:rgba(255,255,255,.1);border-radius:20px;overflow:hidden;margin:16px 0}.fill{height:100%;background:#fa233b;width:{{progress}}%}.btn{display:inline-block;margin-top:18px;padding:12px 18px;border-radius:999px;background:#fa233b;color:white;text-decoration:none;font-weight:700}
</style>
</head>
<body>
<div class="card">
<h1>🎁 ASHPLEX Reward Wallet</h1>
<p class="muted">Daily target: Listen 20 preview songs to unlock ₹10 reward.</p>
<div class="big">₹{{total_rewards}}</div>
<p>Total reward earned</p>
<div class="bar"><div class="fill"></div></div>
<p>{{today_plays}} / 20 songs listened today</p>
<a class="btn" href="/home">Back to Music</a>
</div>

<script>
document.querySelectorAll(".player-info h2").forEach(el=>{
  const txt=document.createElement("textarea");
  txt.innerHTML=el.innerHTML;
  el.innerText=txt.value;
});
</script>
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
        return LOGIN_HTML.replace("Developer: ashutosh / Ashplex@123", "Wrong username or password")

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

    songs = get_deezer_songs(query)

    return render_template_string(
        APP_HTML,
        songs=songs,
        query=query,
        user=session.get("user"),
        role=session.get("role")
    )

@app.route("/youtube")
@login_required
def youtube_mode():
    q = request.args.get("q", "arijit song")
    video = get_youtube_video(q)
    return render_template_string(
        YOUTUBE_HTML,
        q=q,
        video=video
    )


@app.route("/developer")
@developer_required
def developer():
    con = db()
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) AS c FROM users WHERE role='customer'")
    customer_count = cur.fetchone()["c"]

    cur.execute("SELECT COALESCE(SUM(total_plays),0) AS total FROM user_stats")
    total_plays = cur.fetchone()["total"]

    cur.execute("""
        SELECT username, total_plays, today_plays, total_rewards
        FROM user_stats
        ORDER BY total_plays DESC
    """)
    stats = cur.fetchall()

    con.close()

    return render_template_string(
        DEVELOPER_HTML,
        stats=stats,
        customer_count=customer_count,
        total_plays=total_plays
    )

@app.route("/wallet")
@login_required
def wallet():
    username = session.get("user")
    con = db()
    cur = con.cursor()
    cur.execute("SELECT * FROM user_stats WHERE username=?", (username,))
    stat = cur.fetchone()
    con.close()

    today_plays = stat["today_plays"] if stat else 0
    total_rewards = stat["total_rewards"] if stat else 0
    progress = min(100, int((today_plays / 20) * 100))

    return render_template_string(
        WALLET_HTML,
        today_plays=today_plays,
        total_rewards=total_rewards,
        progress=progress
    )

@app.route("/account")
@login_required
def account():
    return render_template_string(ACCOUNT_HTML, user=session.get("user"), role=session.get("role"))

@app.route("/forget-account", methods=["POST"])
@login_required
def forget_account():
    if session.get("role") == "developer":
        return redirect("/account")

    username = session.get("user")
    con = db()
    cur = con.cursor()
    cur.execute("DELETE FROM users WHERE username=? AND role='customer'", (username,))
    cur.execute("DELETE FROM user_stats WHERE username=?", (username,))
    con.commit()
    con.close()
    session.clear()
    return redirect("/")

@app.route("/api/play")
@login_required
def api_play():
    result = update_user_activity(session.get("user"))
    return jsonify({"ok": True, **result})

@app.route("/api/deezer")
def api_deezer():
    q = request.args.get("q", "arijit")
    return jsonify({"query": q, "songs": get_deezer_songs(q)})

@app.route("/api/youtube")
def api_youtube():
    q = request.args.get("q", "arijit")
    video = get_youtube_video(q)
    return jsonify({
        "query": q,
        "video": video,
        "youtube_search_url": youtube_search_url(query=q)
    })


@app.route("/api/user-stats")
@login_required
def api_user_stats():
    username = session.get("user")
    con = db()
    cur = con.cursor()
    cur.execute("SELECT * FROM user_stats WHERE username=?", (username,))
    stat = cur.fetchone()
    con.close()

    if not stat:
        return jsonify({"username": username, "total_plays": 0, "today_plays": 0, "total_rewards": 0})

    return jsonify({
        "username": stat["username"],
        "total_plays": stat["total_plays"],
        "today_plays": stat["today_plays"],
        "total_rewards": stat["total_rewards"],
        "target": 20
    })

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
