import os
import sqlite3
import time
import requests
from flask import Flask, render_template_string, request, redirect, session
from functools import wraps

app = Flask(__name__)
app.secret_key = "smartify_secret"

DB = "database.db"

def db():
    return sqlite3.connect(DB)

# ------------------ LOGIN CHECK ------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect("/")
        return f(*args, **kwargs)
    return wrapper

# ------------------ HOME ------------------
@app.route("/")
def login():
    return """
    <h2>Login</h2>
    <form method="post" action="/login">
    <input name="user"><button>Login</button>
    </form>
    """

@app.route("/login", methods=["POST"])
def do_login():
    session["user"] = request.form["user"]
    return redirect("/home")

# ------------------ HOME PAGE ------------------
@app.route("/home")
@login_required
def home():
    con = db()
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS songs(title, file)")
    songs = cur.fetchall()

    html = "<h1>Smartify 🎧</h1>"
    html += "<a href='/online'>🌐 Online Music</a><br><br>"

    for s in songs:
        html += f"""
        <div>
        <h3>{s[0]}</h3>
        <audio controls>
        <source src='/static/{s[1]}'>
        </audio>
        </div>
        """

    return html

# ------------------ ONLINE API ------------------
@app.route("/online")
@login_required
def online():
    query = request.args.get("q", "arijit")

    try:
        url = f"https://api.deezer.com/search?q={query}"
        data = requests.get(url).json()
        songs = data.get("data", [])
    except:
        songs = []

    html = "<h1>🌐 Online Songs</h1>"
    html += "<form><input name='q'><button>Search</button></form>"

    for s in songs[:10]:
        html += f"""
        <div>
        <img src='{s['album']['cover_medium']}' width=150><br>
        <b>{s['title']}</b><br>
        {s['artist']['name']}<br>
        <audio controls>
        <source src='{s['preview']}'>
        </audio>
        </div><hr>
        """

    return html

# ------------------ RUN ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
