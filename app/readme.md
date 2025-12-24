# Project Documentation

This README documents **what the code does**, file by file. It is based on static analysis of the source code and focuses strictly on behavior and responsibilities, not design opinions.

---

## `main.py`
**Purpose:** Application entry point and runtime orchestrator.

**What it does:**
- Initializes and wires together all major subsystems: audio analysis, face tracking, facial feature extraction, scoring, smoothing, UI overlays, logging, and the web server.
- Captures video frames from a camera using OpenCV.
- Runs a real-time loop that:
  - Tracks faces in the video stream.
  - Extracts facial action units / features.
  - Processes audio input via YAMNet.
  - Computes an amusement score from facial and audio signals.
  - Applies exponential moving average (EMA) smoothing to scores.
  - Renders score overlays and optional debug overlays on the video feed.
- Manages shared application state (current video, playback status, participant metadata, timestamps, etc.).
- Starts and interacts with a Flask web server used for external control and monitoring.
- Opens a browser automatically when the server starts.

---

## `audio/yamnet_audio.py`
**Purpose:** Audio capture and sound classification.

**What it does:**
- Wraps Google’s YAMNet audio classification model.
- Captures microphone audio in real time.
- Converts raw audio into embeddings and class probabilities.
- Tracks audio-based signals relevant to amusement (e.g., laughter, vocal reactions).
- Exposes a `YamnetAudio` class used by the main loop to fetch audio-derived scores or features.

---

## `face/face_tracker.py`
**Purpose:** Face detection and tracking.

**What it does:**
- Detects faces in video frames using a computer vision model.
- Tracks detected faces across frames to maintain consistent identity.
- Outputs bounding boxes and face regions for downstream processing.
- Acts as the first stage of the facial analysis pipeline.

---

## `face/facial_features.py`
**Purpose:** Facial feature and action unit extraction.

**What it does:**
- Receives cropped face regions from the face tracker.
- Extracts facial landmarks and/or action unit–like features.
- Converts facial expressions into numeric signals usable by the scoring system.
- Encapsulated in the `FacialFeatureExtractor` class.

---

## `scoring/scorer.py`
**Purpose:** Amusement score computation.

**What it does:**
- Combines facial features and audio features into a single amusement score.
- Applies weighting and heuristic logic to estimate amusement intensity.
- Exposes an `AmusementScorer` class used in the main loop.

---

## `utils/smoothing.py`
**Purpose:** Temporal smoothing of noisy signals.

**What it does:**
- Implements an Exponential Moving Average (EMA) smoother.
- Reduces jitter in amusement scores across frames.
- Used to stabilize visual output and logged data.

---

## `utils/geometry.py`
**Purpose:** Geometry and coordinate utilities.

**What it does:**
- Provides helper functions for bounding boxes, points, and spatial calculations.
- Supports face tracking and overlay rendering logic.

---

## `ui/overlay.py`
**Purpose:** Visual score overlay rendering.

**What it does:**
- Draws the amusement score and related UI elements onto video frames.
- Uses OpenCV drawing utilities.
- Designed for end-user display (non-debug view).

---

## `ui/au_debug_overlay.py`
**Purpose:** Debug visualization for facial features.

**What it does:**
- Renders detailed facial action unit or feature values on the video feed.
- Intended for development and debugging.
- Can be enabled or disabled independently of the main overlay.

---

## `logger/text_logger.py`
**Purpose:** Persistent logging of session data.

**What it does:**
- Writes amusement scores, timestamps, and participant metadata to text logs.
- Appends structured data to files under the `logs/` directory.
- Used for offline analysis and evaluation.

---

## `web/server.py`
**Purpose:** Web-based control and monitoring interface.

**What it does:**
- Implements a Flask web server.
- Exposes HTTP endpoints to:
  - Control playback state (start, stop, reset).
  - Set participant metadata (name, age, gender).
  - Query current amusement score and runtime state.
- Shares state with `main.py` via a global/shared structure.
- Disables default Flask logging for cleaner console output.

---

## Runtime Artifacts

### `logs/log.txt`
- Stores text-based logs generated during application execution.

### `__pycache__/`
- Python bytecode cache generated automatically at runtime.
- Not part of the application logic.

---

## Summary
This project is a real-time amusement detection system that:
- Analyzes facial expressions and audio input.
- Computes and smooths an amusement score.
- Displays results live on video.
- Logs session data.
- Provides a web interface for external control.

All behavior described above is derived directly from the source code structure and implementation.

