import threading
import logging
from flask import Flask, render_template, request, jsonify, render_template_string

# Disable default Flask logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

# Shared state
STATE = {
    "current_video_id": "WAITING",
    "is_playing": False,
    "finished": False,
    "video_time": 0.0,
    # New fields for participant info
    "participant": None,  # Will hold {"name":..., "age":..., "gender":...}
    "ready_to_start": False  # Flag to tell main.py that registration is done
}

current_playlist_ids = []


def set_playlist(video_ids):
    global current_playlist_ids
    current_playlist_ids = video_ids


# 1. The Root URL now shows the FORM
@app.route('/')
def index():
    return render_template('form.html')


# 2. Handle Form Submission
@app.route('/start', methods=['POST'])
def start_experiment():
    # Save participant info to state
    STATE["participant"] = {
        "name": request.form.get("name"),
        "age": request.form.get("age"),
        "gender": request.form.get("gender")
    }
    STATE["ready_to_start"] = True

    # Now render the player
    return render_template('player.html', playlist=current_playlist_ids)


@app.route('/status', methods=['POST'])
def update_status():
    data = request.json
    STATE["current_video_id"] = data.get("video_id", "UNKNOWN")
    STATE["is_playing"] = data.get("playing", False)
    STATE["video_time"] = data.get("timestamp", 0.0)

    if data.get("status") == "playlist_ended":
        STATE["finished"] = True

    return jsonify(success=True)


def run_server():
    app.run(port=5000, use_reloader=False)


def start_background_server():
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    return STATE