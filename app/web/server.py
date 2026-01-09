import threading
import logging
import os
import sqlite3

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    render_template_string,
    redirect,
    session
)

# Disable default Flask logging
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

# ===== Config =====
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.db"))
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "affectivecomputing2025")

# IMPORTANT:
# Use rowid parity for splitting work between two reviewers.
# 1 = odd rowid, 0 = even rowid
ADMIN_ROWID_PARITY = 1  # <-- YOU keep 1 (odd). Your friend sets this to 0 (even).

# Shared state for experiment
STATE = {
    "current_video_id": "WAITING",
    "is_playing": False,
    "finished": False,
    "video_time": 0.0,
    "participant": None,       # {"name":..., "age":..., "gender":...}
    "ready_to_start": False
}

# Admin review pointer (single-user lab usage)
# (kept; no longer required for random selection, but not harmful)
ADMIN_STATE = {
    "last_rowid": 0
}

current_playlist_ids = []


def set_playlist(video_ids):
    global current_playlist_ids
    current_playlist_ids = video_ids


# ===== DB helpers =====
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def admin_get_next_video(*, after_rowid: int = 0, only_na: bool = True):
    """
    Returns ONE random video for admin review.
    - Splits workload by rowid parity (odd/even) using ADMIN_ROWID_PARITY.
    - If only_na=True: returns only rows needing review (status is NULL or 'n/a')
    - after_rowid kept for compatibility, but intentionally not used with RANDOM selection.
    """
    if only_na:
        where_status = "AND (status IS NULL OR status = 'n/a')"
    else:
        where_status = ""

    # Key fix: DO NOT cast YouTube vid to integer.
    # Use rowid parity for odd/even split.
    query = f"""
        SELECT rowid, vid, link, duration, status
        FROM Video
        WHERE vid IS NOT NULL AND TRIM(vid) <> ''
          AND (rowid % 2) = ?
          {where_status}
        ORDER BY RANDOM()
        LIMIT 1
    """

    with get_db() as conn:
        row = conn.execute(query, (ADMIN_ROWID_PARITY,)).fetchone()

    return row


def admin_update_status(vid: str, status: str):
    with get_db() as conn:
        conn.execute("UPDATE Video SET status=? WHERE vid=?", (status, vid))
        conn.commit()


# ===== Routes: Experiment =====
@app.route("/")
def index():
    return render_template("form.html")


@app.route("/start", methods=["POST"])
def start_experiment():
    STATE["participant"] = {
        "name": request.form.get("name"),
        "age": request.form.get("age"),
        "gender": request.form.get("gender")
    }
    STATE["ready_to_start"] = True
    return render_template("player.html", playlist=current_playlist_ids)


@app.route("/status", methods=["POST"])
def update_status():
    data = request.json or {}
    STATE["current_video_id"] = data.get("video_id", "UNKNOWN")
    STATE["is_playing"] = data.get("playing", False)
    STATE["video_time"] = data.get("timestamp", 0.0)

    if data.get("status") == "playlist_ended":
        STATE["finished"] = True

    return jsonify(success=True)


# ===== Routes: Admin/Test =====
@app.route("/admin")
def admin_login():
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Admin Login</title>
            <style>
                body { font-family:sans-serif; display:flex; justify-content:center; align-items:center; height:100vh; background:#111; color:white; }
                .box { background:#222; padding:30px; border-radius:8px; width:320px; box-shadow: 0 0 20px rgba(0,0,0,0.4); }
                input, button { width:100%; padding:10px; margin-top:10px; box-sizing:border-box; border-radius:6px; border:1px solid #444; }
                input { background:#111; color:#fff; }
                button { background:#4CAF50; border:none; color:white; font-size:16px; cursor:pointer; }
                button:hover { background:#43a047; }
                .hint { margin-top:12px; font-size:12px; opacity:0.8; }
            </style>
        </head>
        <body>
            <div class="box">
                <h2>Admin / Test Mode</h2>
                <form action="/admin/login" method="POST">
                    <input type="password" name="password" placeholder="Password" required>
                    <button type="submit">Enter</button>
                </form>
                <div class="hint">
                    Tip: set ADMIN_PASSWORD in your terminal before running.
                </div>
            </div>
        </body>
        </html>
    """)


@app.route("/admin/login", methods=["POST"])
def admin_login_post():
    pw = request.form.get("password", "")
    if pw != ADMIN_PASSWORD:
        return "Unauthorized", 401

    session["is_admin"] = True
    ADMIN_STATE["last_rowid"] = 0  # kept

    # Default: review only n/a videos
    return redirect("/admin/review?only_na=1")


@app.route("/admin/review")
def admin_review():
    if not session.get("is_admin"):
        return redirect("/admin")

    only_na = request.args.get("only_na", "1") == "1"

    # Random selection across ALL matching videos (by rowid parity + status filter)
    row = admin_get_next_video(after_rowid=ADMIN_STATE["last_rowid"], only_na=only_na)

    if row is None:
        msg = "No more n/a videos to review." if only_na else "No more videos to review."
        toggle = "/admin/review?only_na=0" if only_na else "/admin/review?only_na=1"
        toggle_text = "Review ALL videos" if only_na else "Review only n/a videos"
        return f"<h2>{msg}</h2><p><a href='{toggle}'>{toggle_text}</a></p>"

    current_rowid = int(row["rowid"])
    vid = row["vid"]
    status = row["status"]

    return render_template_string(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Admin Review</title>
        <style>
            body {{ margin:0; background:#000; color:#fff; font-family:sans-serif; }}
            .topbar {{
                position:fixed; top:0; left:0; right:0;
                padding:12px; background:rgba(0,0,0,0.85);
                display:flex; gap:10px; align-items:center; z-index:10;
            }}
            button {{
                padding:10px 14px; border:none; border-radius:8px;
                cursor:pointer; font-size:16px;
            }}
            .approve {{ background:#2e7d32; color:white; }}
            .deny {{ background:#c62828; color:white; }}
            .skip {{ background:#555; color:white; }}
            .meta {{ margin-left:auto; opacity:0.9; font-size:14px; }}
            a {{ color:#9cf; }}
            iframe {{ width:100vw; height:100vh; border:0; }}
            .spacer {{ height:64px; }}
        </style>
    </head>
    <body>
        <div class="topbar">
            <button class="approve" onclick="setStatus('approved')">Approve</button>
            <button class="deny" onclick="setStatus('denied')">Deny</button>
            <button class="skip" onclick="setStatus('n/a')">Skip</button>

            <div class="meta">
                only_na=<b>{'1' if only_na else '0'}</b> |
                rowid=<b>{current_rowid}</b> |
                vid=<b>{vid}</b> |
                status=<b>{status}</b> |
                parity=<b>{ADMIN_ROWID_PARITY}</b> |
                <a href="/admin/review?only_na={'0' if only_na else '1'}">toggle only_na</a>
            </div>
        </div>

        <div class="spacer"></div>

        <iframe
            src="https://www.youtube.com/embed/{vid}?autoplay=1&controls=1&rel=0&playsinline=1"
            allow="autoplay; encrypted-media"
            allowfullscreen>
        </iframe>

        <script>
            async function setStatus(newStatus) {{
                const res = await fetch('/admin/set_status', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        vid: '{vid}',
                        status: newStatus,
                        rowid: {current_rowid}
                    }})
                }});

                if (!res.ok) {{
                    const txt = await res.text();
                    alert('Failed to update status: ' + txt);
                    return;
                }}

                // go to next video, preserve filter
                window.location.href = '/admin/review?only_na=' + ({'1' if only_na else '0'});
            }}
        </script>
    </body>
    </html>
    """)


@app.route("/admin/set_status", methods=["POST"])
def admin_set_status():
    if not session.get("is_admin"):
        return "Forbidden", 403

    data = request.json or {}
    vid = data.get("vid")
    status = data.get("status")
    rowid = data.get("rowid")

    if status not in ("approved", "denied", "n/a"):
        return "Invalid status", 400
    if not vid or rowid is None:
        return "Missing vid/rowid", 400

    admin_update_status(vid, status)

    # (kept) update pointer even though selection is random; harmless
    ADMIN_STATE["last_rowid"] = int(rowid)

    return jsonify({"ok": True})


# ===== Server startup =====
def run_server():
    app.run(port=5000, use_reloader=False)


def start_background_server():
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    return STATE