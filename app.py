import os
import requests
from functools import wraps
from flask import Flask, render_template_string, request, redirect, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "smartify_secret")

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect("/")
        return f(*args, **kwargs)
    return wrapper

def get_online_songs(query="arijit"):
    try:
        url = f"https://api.deezer.com/search?q={query}"
        data = requests.get(url, timeout=10).json()
        songs = []
        for s in data.get("data", [])[:16]:
            songs.append({
                "title": s.get("title", "Unknown"),
                "artist": s.get("artist", {}).get("name", "Unknown"),
                "cover": s.get("album", {}).get("cover_medium", ""),
                "preview": s.get("preview", "")
            })
        return songs
    except Exception:
        return []

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>ASHPLEX Login</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body{margin:0;background:#090910;color:white;font-family:Arial;height:100vh;display:flex;align-items:center;justify-content:center}
.box{background:#141420;padding:35px;border-radius:18px;width:340px;text-align:center;border:1px solid #2a2440}
h1{color:#e0345a}
input{width:90%;padding:13px;margin:9px;border-radius:12px;border:1px solid #2a2440;background:#090910;color:white}
button{background:#e0345a;color:white;border:0;border-radius:20px;padding:12px 25px;font-weight:bold}
</style>
</head>
<body>
<div class="box">
<h1>🎧 ASHPLEX</h1>
<p style="color:#aaa;margin-top:-5px">Your Mood. Your Music. Your World.</p>
<h2>Login</h2>
<form method="POST" action="/login">
<input name="user" placeholder="Username" required>
<input name="password" type="password" placeholder="Password">
<button>Login</button>
</form>
<p style="color:#777">Use any username</p>
</div>
</body>
</html>
"""

UI = """
<!DOCTYPE html>
<html>
<head>
<title>ASHPLEX</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=Bebas+Neue&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{background:#05050a;min-height:100vh;display:flex;align-items:center;justify-content:center}
.app{display:grid;grid-template-columns:210px 1fr;grid-template-rows:1fr 72px;width:100%;max-width:1180px;height:680px;background:#0d0d14;color:#e2ddf0;font-family:'DM Sans',sans-serif;border-radius:14px;overflow:hidden;font-size:13px}
.sidebar{background:#090910;border-right:0.5px solid #1e1a30;display:flex;flex-direction:column;overflow:hidden;grid-row:1/2}
.sb-logo{padding:16px 16px 8px;display:flex;align-items:center;gap:8px}
.logo-mark{width:26px;height:26px;border-radius:6px;background:#e0345a;display:flex;align-items:center;justify-content:center;font-size:14px}
.logo-text{font-family:'Bebas Neue',sans-serif;font-size:18px;color:#e2ddf0;letter-spacing:1px}
.sb-search{margin:8px 12px;position:relative}
.sb-search input{width:100%;background:#141420;border:0.5px solid #2a2440;border-radius:8px;padding:7px 10px 7px 30px;color:#e2ddf0;font-size:12px;outline:none;font-family:'DM Sans',sans-serif}
.sb-search button{display:none}
.sb-search-ico{position:absolute;left:9px;top:8px;color:#4a4568;font-size:13px}
.sb-section{padding:10px 12px 4px;font-size:10px;letter-spacing:1.2px;color:#3a3558;text-transform:uppercase;font-weight:600}
.sb-item{display:flex;align-items:center;gap:9px;padding:8px 14px;cursor:pointer;border-radius:0;color:#7a739a;transition:all 0.15s;border-left:2px solid transparent;text-decoration:none}
.sb-item:hover{color:#c9c0e8;background:#121220}
.sb-item.active{color:#fff;background:#15122a;border-left:2px solid #e0345a}
.sb-item-ico{width:16px;text-align:center;font-size:15px;flex-shrink:0}
.sb-item-txt{font-size:13px}
.sb-divider{height:0.5px;background:#1a1728;margin:6px 12px}
.sb-new-pl{display:flex;align-items:center;gap:8px;padding:9px 14px;cursor:pointer;color:#4a4568;margin-top:auto;border-top:0.5px solid #1a1728}
.main{overflow-y:auto;display:flex;flex-direction:column;scrollbar-width:thin;scrollbar-color:#1e1a30 transparent}
.main::-webkit-scrollbar{width:4px}.main::-webkit-scrollbar-track{background:transparent}.main::-webkit-scrollbar-thumb{background:#1e1a30;border-radius:4px}
.hero{position:relative;height:230px;flex-shrink:0;overflow:hidden}
.hero-bg{position:absolute;inset:0;background:linear-gradient(135deg,#1a0a2e 0%,#0a1a3a 60%,#1a0a18 100%);display:flex;align-items:center;justify-content:center}
.hero-circles{position:absolute;inset:0}.hc{position:absolute;border-radius:50%;opacity:0.07}
.hero-content{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:flex-end;padding:24px}
.hero-tag{font-size:11px;letter-spacing:1.5px;color:#e0345a;text-transform:uppercase;font-weight:600;margin-bottom:6px}
.hero-title{font-family:'Bebas Neue',sans-serif;font-size:48px;color:#fff;line-height:0.95;margin-bottom:8px;letter-spacing:2px}
.hero-sub{font-size:12px;color:#8a80a8;margin-bottom:14px}
.hero-actions{display:flex;gap:8px;align-items:center}
.btn-primary{background:#e0345a;color:#fff;border:none;padding:8px 20px;border-radius:20px;font-size:12px;font-weight:600;cursor:pointer;font-family:'DM Sans',sans-serif;text-decoration:none}
.btn-outline{background:transparent;color:#c9c0e8;border:0.5px solid #3a2f6a;padding:8px 16px;border-radius:20px;font-size:12px;cursor:pointer;font-family:'DM Sans',sans-serif;text-decoration:none}
.btn-outline:hover{border-color:#e0345a;color:#e0345a}
.hero-rec{font-size:10px;color:#4a4568;margin-top:10px;letter-spacing:0.5px}.hero-rec span{color:#7a6fa0}
.content-area{display:grid;grid-template-columns:1fr 260px;gap:0;flex:1}
.main-col{padding:16px 16px 0}.side-col{border-left:0.5px solid #1a1728;overflow-y:auto;scrollbar-width:none}.side-col::-webkit-scrollbar{display:none}
.sec-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
.sec-title{font-size:11px;letter-spacing:1.2px;color:#4a4568;text-transform:uppercase;font-weight:600}
.sec-more{font-size:12px;color:#7c3aed;cursor:pointer}
.tracks-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(100px,1fr));gap:10px;margin-bottom:18px}
.track-card{cursor:pointer;border-radius:8px;overflow:hidden;background:#141420;border:0.5px solid #1e1a30;transition:border-color 0.15s}
.track-card:hover{border-color:#3a2f6a}
.tc-art{height:88px;background:#1e1a30;display:flex;align-items:center;justify-content:center;font-size:28px;position:relative}
.tc-art img{width:100%;height:100%;object-fit:cover}
.tc-play-overlay{position:absolute;inset:0;background:rgba(0,0,0,0.5);display:none;align-items:center;justify-content:center;font-size:22px}
.track-card:hover .tc-play-overlay{display:flex}
.tc-info{padding:7px 8px}.tc-name{font-size:12px;color:#c9c0e8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:500;margin-bottom:2px}.tc-artist{font-size:11px;color:#4a4568;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mood-row{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:18px}
.mood-pill{padding:6px 14px;border-radius:20px;border:0.5px solid #2a2440;color:#7a739a;font-size:12px;cursor:pointer;transition:all 0.15s;background:#141420;text-decoration:none}
.mood-pill:hover,.mood-pill.on{background:#2a1a50;border-color:#7c3aed;color:#c084fc}
.ai-suggest{background:#13101f;border:0.5px solid #2a1f45;border-radius:10px;padding:12px;margin-bottom:18px}
.ai-head{display:flex;align-items:center;gap:8px;margin-bottom:10px}.ai-dot{width:8px;height:8px;border-radius:50%;background:#e0345a;animation:pulse 1.5s infinite}.ai-label{font-size:11px;color:#e0345a;letter-spacing:0.8px;text-transform:uppercase;font-weight:600}
.ai-chips{display:flex;gap:6px;flex-wrap:wrap}.ai-chip{font-size:11px;padding:5px 12px;border-radius:16px;background:#1e1530;border:0.5px solid #2e2055;color:#9b75e0;cursor:pointer;transition:all 0.15s;text-decoration:none}.ai-chip:hover,.ai-chip.on{background:#2e1760;border-color:#7c3aed;color:#d4b8ff}
.tracklist{padding:0 12px 12px}.tl-head{display:flex;align-items:center;gap:8px;padding:10px 12px 6px;font-size:11px;color:#e0345a;letter-spacing:1px;text-transform:uppercase;font-weight:600;border-bottom:0.5px solid #1a1728;margin-bottom:4px}
.tl-item{display:flex;align-items:center;gap:10px;padding:8px 12px;cursor:pointer;border-radius:0;transition:background 0.1s}
.tl-item:hover{background:#13101f}.tl-item.playing{background:#150f2a}
.tl-num{font-size:12px;color:#3a3558;width:16px;text-align:right;flex-shrink:0}.tl-play-ico{width:16px;text-align:center;display:none;color:#e0345a;font-size:14px;flex-shrink:0}.tl-item.playing .tl-num{display:none}.tl-item.playing .tl-play-ico{display:block}
.tl-info{flex:1;min-width:0}.tl-name{font-size:13px;color:#c9c0e8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.tl-item.playing .tl-name{color:#e0345a}.tl-artist{font-size:11px;color:#4a4568;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.tl-heart{color:#3a3558;font-size:14px;cursor:pointer;padding:2px 6px;flex-shrink:0}.tl-heart.liked{color:#e0345a}.tl-dur{font-size:12px;color:#3a3558;flex-shrink:0;width:32px;text-align:right}
.rec-card{margin:12px;border-radius:10px;overflow:hidden;background:#e0345a;padding:14px;cursor:pointer;position:relative}.rec-bg{position:absolute;inset:0;background:radial-gradient(circle at 70% 30%,rgba(255,255,255,0.08),transparent)}
.rec-label{font-size:10px;letter-spacing:1px;color:rgba(255,255,255,0.7);text-transform:uppercase;margin-bottom:4px;position:relative}.rec-title{font-family:'Bebas Neue',sans-serif;font-size:22px;color:#fff;letter-spacing:1px;position:relative}.rec-play{width:38px;height:38px;border-radius:50%;background:rgba(255,255,255,0.2);border:1.5px solid rgba(255,255,255,0.5);display:flex;align-items:center;justify-content:center;margin:10px 0;cursor:pointer;position:relative}.rec-play-tri{width:0;height:0;border-top:7px solid transparent;border-bottom:7px solid transparent;border-left:11px solid #fff;margin-left:2px}.rec-sub{font-size:10px;color:rgba(255,255,255,0.6);position:relative}
.player{grid-column:1/3;background:#0a0914;border-top:0.5px solid #1e1a30;display:flex;align-items:center;padding:0 20px;gap:16px}
.pl-art{width:44px;height:44px;border-radius:7px;background:#1e1a30;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:20px;overflow:hidden}
.pl-art img{width:100%;height:100%;object-fit:cover}.pl-info{min-width:0;flex:0 0 180px}.pl-title{font-size:13px;font-weight:500;color:#e2ddf0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.pl-artist{font-size:11px;color:#4a4568}.pl-heart{color:#e0345a;font-size:16px;cursor:pointer;flex-shrink:0;padding:0 4px}.pl-add{color:#4a4568;font-size:16px;cursor:pointer;flex-shrink:0;padding:0 4px}
.pl-controls{display:flex;align-items:center;gap:14px;flex:1;justify-content:center}.pl-btn{background:none;border:none;color:#7a739a;cursor:pointer;font-size:18px;padding:4px;transition:color 0.15s}.pl-btn:hover{color:#e2ddf0}.pl-btn.on{color:#e0345a}.pl-play{width:38px;height:38px;border-radius:50%;background:#e0345a;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0}.pl-play-tri{width:0;height:0;border-top:8px solid transparent;border-bottom:8px solid transparent;border-left:12px solid #fff;margin-left:3px}.pl-pause{color:white;font-size:18px;font-weight:bold}
.pl-progress{flex:1;max-width:280px;display:flex;align-items:center;gap:8px}.pl-prog-bar{flex:1;height:3px;background:#1e1a30;border-radius:3px;cursor:pointer;position:relative}.pl-prog-fill{height:100%;width:15%;background:#e0345a;border-radius:3px}.pl-time{font-size:11px;color:#3a3558;white-space:nowrap}
.pl-right{display:flex;align-items:center;gap:10px;flex:0 0 160px;justify-content:flex-end}.pl-vol-bar{width:80px;height:3px;background:#1e1a30;border-radius:3px;cursor:pointer;position:relative}.pl-vol-fill{height:100%;width:60%;background:#7a739a;border-radius:3px}.pl-ico{font-size:16px;color:#4a4568;cursor:pointer;padding:2px}.pl-ico:hover{color:#e2ddf0}
.hidden-audio{display:none}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}
@media(max-width:820px){
  body{display:block;background:#0d0d14}
  .app{display:block;height:auto;min-height:100vh;border-radius:0;padding-bottom:86px}
  .sidebar{display:none}
  .hero{height:210px}
  .hero-title{font-size:40px}
  .content-area{display:block}
  .side-col{display:none}
  .tracks-grid{grid-template-columns:1fr}
  .track-card{display:grid;grid-template-columns:86px 1fr;align-items:center}
  .tc-art{height:86px}
  .player{position:fixed;left:0;right:0;bottom:0;height:86px;grid-column:auto;padding:0 12px}
  .pl-controls,.pl-progress,.pl-right,.pl-add{display:none}
  .pl-info{flex:1}
}
</style>
</head>
<body>
<div class="app">
  <div class="sidebar">
    <div class="sb-logo"><div class="logo-mark">♪</div><div class="logo-text">ASHPLEX</div></div>
    <form class="sb-search" action="/home"><span class="sb-search-ico">⌕</span><input name="q" value="{{query}}" placeholder="What are you looking for?"><button>Search</button></form>
    <div class="sb-section">Music</div>
    <a class="sb-item active" href="/home"><span class="sb-item-ico">◈</span><span class="sb-item-txt">Discover</span></a>
    <a class="sb-item" href="/home?q=arijit"><span class="sb-item-ico">◎</span><span class="sb-item-txt">Collection</span></a>
    <a class="sb-item" href="/home?q=lofi"><span class="sb-item-ico">⊕</span><span class="sb-item-txt">Connect</span></a>
    <a class="sb-item" href="/home?q=punjabi"><span class="sb-item-ico">◉</span><span class="sb-item-txt">Radio</span></a>
    <div class="sb-divider"></div>
    <div class="sb-section">Playlists</div>
    <a class="sb-item" href="/home?q=love"><span class="sb-item-ico">★</span><span class="sb-item-txt">Favourites</span></a>
    <a class="sb-item" href="/home?q=night"><span class="sb-item-ico">♪</span><span class="sb-item-txt">Late Night Vibes</span></a>
    <a class="sb-item" href="/home?q=workout"><span class="sb-item-ico">♪</span><span class="sb-item-txt">Workout Mix</span></a>
    <a class="sb-item" href="/home?q=focus"><span class="sb-item-ico">♪</span><span class="sb-item-txt">Focus Mode</span></a>
    <a class="sb-item" href="/logout"><span class="sb-item-ico">⇥</span><span class="sb-item-txt">Logout</span></a>
    <div class="sb-new-pl"><span style="font-size:16px">⊕</span><span>New Playlist</span></div>
  </div>

  <div class="main">
    <div class="hero">
      <div class="hero-bg"><div class="hero-circles">
        <div class="hc" style="width:300px;height:300px;background:#7c3aed;top:-80px;right:40px"></div>
        <div class="hc" style="width:180px;height:180px;background:#e0345a;bottom:-40px;right:120px"></div>
        <div class="hc" style="width:120px;height:120px;background:#3b0764;top:20px;right:200px"></div>
      </div></div>
      <div class="hero-content">
        <div class="hero-tag">🎧 ASHPLEX — Your Mood. Your Music. Your World.</div>
        <div class="hero-title">ASHPLEX</div>
        <div class="hero-sub">🎧 Your Mood. Your Music. Your World. · {{songs|length}} tracks</div>
        <div class="hero-actions">
          <a class="btn-primary" href="/home?q={{query}}">▶ Play All</a>
          <a class="btn-outline" href="/home?q=lofi">Radio</a>
          <a class="btn-outline" href="/home?q=workout">Workout</a>
        </div>
        <div class="hero-rec">Recommendation based on: <span>{{query}}</span></div>
      </div>
    </div>

    <div class="content-area">
      <div class="main-col">
        <div class="sec-head"><span class="sec-title">Mood detector</span></div>
        <div class="mood-row">
          <a class="mood-pill on" href="/home?q=night">🌙 Late Night</a>
          <a class="mood-pill on" href="/home?q=dreamy">✨ Dreamy</a>
          <a class="mood-pill" href="/home?q=energetic">⚡ Energetic</a>
          <a class="mood-pill" href="/home?q=happy">☀️ Happy</a>
          <a class="mood-pill" href="/home?q=focus">🎯 Focus</a>
          <a class="mood-pill" href="/home?q=relax">💆 Relax</a>
        </div>

        <div class="ai-suggest">
          <div class="ai-head"><div class="ai-dot"></div><div class="ai-label">AI smart suggestions</div></div>
          <div class="ai-chips">
            <a class="ai-chip on" href="/home?q=retro">Retro Drive</a>
            <a class="ai-chip" href="/home?q=synthwave">Synthwave 80s</a>
            <a class="ai-chip" href="/home?q=night city">Night City</a>
            <a class="ai-chip" href="/home?q=deep focus">Deep Focus</a>
          </div>
        </div>

        <div class="sec-head"><span class="sec-title">Hot Tracks Worldwide</span><span class="sec-more">Search: {{query}}</span></div>
        <div class="tracks-grid">
          {% for s in songs %}
          <div class="track-card" onclick="playSong('{{s.preview}}','{{s.title|e}}','{{s.artist|e}}','{{s.cover}}')">
            <div class="tc-art"><img src="{{s.cover}}"><div class="tc-play-overlay">▶</div></div>
            <div class="tc-info"><div class="tc-name">{{s.title}}</div><div class="tc-artist">{{s.artist}}</div></div>
          </div>
          {% else %}
          <p style="color:#777">No songs found. Try another search.</p>
          {% endfor %}
        </div>
      </div>

      <div class="side-col">
        <div class="tl-head"><span>Best Tracks · Worldwide</span></div>
        <div class="tracklist">
          {% for s in songs[:10] %}
          <div class="tl-item {% if loop.index==1 %}playing{% endif %}" onclick="playSong('{{s.preview}}','{{s.title|e}}','{{s.artist|e}}','{{s.cover}}')">
            <span class="tl-num">{{loop.index}}</span><span class="tl-play-ico">▶</span>
            <div class="tl-info"><div class="tl-name">{{s.title}}</div><div class="tl-artist">{{s.artist}}</div></div>
            <span class="tl-heart">♥</span><span class="tl-dur">3:20</span>
          </div>
          {% endfor %}
        </div>

        <div class="rec-card">
          <div class="rec-bg"></div><div class="rec-label">Recommended · Best Tracks</div>
          <div class="rec-title">Top Picks</div><div class="rec-play"><div class="rec-play-tri"></div>
          </div><div class="rec-sub">Search and preview playlist</div>
        </div>
      </div>
    </div>
  </div>

  <div class="player">
    <div class="pl-art" id="plArt">{% if songs %}<img src="{{songs[0].cover}}">{% else %}🎵{% endif %}</div>
    <div class="pl-info">
      <div class="pl-title" id="plTitle">{% if songs %}{{songs[0].title}}{% else %}No Song{% endif %}</div>
      <div class="pl-artist" id="plArtist">{% if songs %}{{songs[0].artist}}{% else %}Search songs{% endif %}</div>
    </div>
    <span class="pl-heart">♥</span><span class="pl-add">+</span>
    <div class="pl-controls"><button class="pl-btn on">⇄</button><button class="pl-btn">⏮</button><button class="pl-play" id="mainPlay"><div class="pl-play-tri" id="mainPlayIco"></div></button><button class="pl-btn">⏭</button><button class="pl-btn on">↺</button></div>
    <div class="pl-progress"><span class="pl-time">0:00</span><div class="pl-prog-bar"><div class="pl-prog-fill"></div></div><span class="pl-time">0:30</span></div>
    <div class="pl-right"><span class="pl-ico">≡</span><span class="pl-ico">◁</span><div class="pl-vol-bar"><div class="pl-vol-fill"></div></div><span class="pl-ico">▷</span></div>
  </div>
</div>

<audio id="mainAudio" class="hidden-audio" {% if songs %}src="{{songs[0].preview}}"{% endif %}></audio>

<script>
const audio = document.getElementById('mainAudio');
const btn = document.getElementById('mainPlay');
const ico = document.getElementById('mainPlayIco');

function playSong(src,title,artist,cover){
  if(!src){return;}
  audio.src = src;
  document.getElementById('plTitle').innerText = title;
  document.getElementById('plArtist').innerText = artist;
  document.getElementById('plArt').innerHTML = '<img src="'+cover+'">';
  audio.play();
  ico.className = 'pl-pause';
  ico.innerHTML = '❚❚';
}

btn.addEventListener('click',()=>{
  if(audio.paused){
    audio.play();
    ico.className='pl-pause';
    ico.innerHTML='❚❚';
  }else{
    audio.pause();
    ico.className='pl-play-tri';
    ico.innerHTML='';
  }
});

document.querySelectorAll('.tl-heart').forEach(h=>h.addEventListener('click',function(e){e.stopPropagation();this.classList.toggle('liked')}));
</script>
</body>
</html>
"""

@app.route("/")
def login():
    return LOGIN_HTML

@app.route("/login", methods=["POST"])
def do_login():
    session["user"] = request.form.get("user", "guest")
    return redirect("/home")

@app.route("/home")
@login_required
def home():
    query = request.args.get("q", "arijit")
    songs = get_online_songs(query)
    return render_template_string(UI, songs=songs, query=query)

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
