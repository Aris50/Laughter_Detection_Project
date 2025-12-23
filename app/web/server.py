import threading
import logging
from flask import Flask, render_template, request, jsonify

# Disable Flask default logging to keep your console clean
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

# Shared state to communicate with main.py
STATE = {
    "current_video_id": "WAITING",  # Default state
    "is_playing": False,
    "finished": False
}

# Variable to hold the generated playlist
current_playlist_ids = []


def set_playlist(video_ids):
    """Called by main.py to set the videos before server starts"""
    global current_playlist_ids
    current_playlist_ids = video_ids


@app.route('/')
def index():
    """Serves the HTML player with the specific playlist"""
    return render_template('player.html', playlist=current_playlist_ids)


@app.route('/status', methods=['POST'])
def update_status():
    """Receives updates from the browser (JS)"""
    data = request.json
    STATE["current_video_id"] = data.get("video_id", "UNKNOWN")
    STATE["is_playing"] = data.get("playing", False)

    if data.get("status") == "playlist_ended":
        STATE["finished"] = True

    return jsonify(success=True)


def run_server():
    """Starts the server in a thread"""
    app.run(port=5000, use_reloader=False)


def start_background_server():
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    return STATE