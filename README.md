# Laughter & Amusement Detection System

A real-time multimodal research application that measures how amused a person is while watching short YouTube videos. The system captures **facial expressions** (via webcam) and **audio reactions** (via microphone) simultaneously, fuses them into a composite **Amusement Score**, and persists all data to a SQLite database for post-experiment analysis.

Built for academic research into humor perception — studying what content makes people laugh, and how measurably amused they are. Used in a real research study with **30 participants** across **~2,000 curated YouTube videos** spanning 7 humor categories.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [System Architecture](#system-architecture)
- [Experiment Flow](#experiment-flow)
- [Scoring Model](#scoring-model)
- [Database Schema](#database-schema)
- [How to Run](#how-to-run)
- [Project Structure](#project-structure)
- [Documents](#documents)

---

## Features

| Feature | Description |
|---|---|
| **Real-time face tracking** | MediaPipe FaceLandmarker (468 landmarks) detects and tracks the participant's face via webcam in real time. |
| **Facial Action Unit estimation** | Extracts three FACS-inspired signals: **AU25** (mouth openness), **AU12** (lip corner puller / smile), **AU6** (cheek raiser via eye-narrowing). Includes automatic per-session neutral baseline calibration. |
| **Audio laughter detection** | Google YAMNet (TFLite) runs on a background thread, continuously classifying microphone input. Sums probabilities of AudioSet classes for Laughter, Giggle, and Chuckle into a single audio score. |
| **Composite amusement scoring** | Weighted fusion of facial + audio signals into three scores: **Smile**, **Laughter**, and **Amusement** (see [Scoring Model](#scoring-model)). |
| **EMA smoothing** | All raw signals are passed through Exponential Moving Average smoothers (α=0.3) to reduce frame-to-frame jitter. |
| **Web-based participant interface** | Flask server hosts a registration form and a YouTube video player. Participants interact only through the browser — no technical knowledge needed. |
| **Randomized playlists** | Each session gets a unique ~7-minute playlist randomly assembled from a curated video pool. |
| **YouTube IFrame player** | Videos play natively via the YouTube IFrame API. Playback state (video ID, timestamp, play/pause) is reported to the backend every 200ms for precise score–video synchronization. |
| **SQLite persistence** | All experiment data (subjects, experiments, per-video scores, session totals) is stored via SQLAlchemy ORM for structured post-hoc analysis. |
| **Per-frame CSV logging** | Timestamped logs with video IDs, all AU values, and all composite scores — enables fine-grained temporal analysis of individual sessions. |
| **Debug overlay** | Optional OpenCV window showing live AU bar gauges and score readouts on the webcam feed for real-time monitoring. |
| **Admin review panel** | Password-protected web interface for researchers to review and approve/deny harvested videos. Supports parallel workload splitting between two reviewers via rowid parity. |
| **Automated video harvester** | `yt-dlp`-based pipeline that searches YouTube by category-specific queries and bulk-inserts candidate videos (filtered by duration) into the database for review. |

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Computer Vision** | OpenCV, MediaPipe FaceLandmarker |
| **Audio Classification** | Google YAMNet (TensorFlow Lite) |
| **Backend** | Python, Flask |
| **Frontend** | HTML/CSS/JS, YouTube IFrame API |
| **Database** | SQLite, SQLAlchemy ORM |
| **Data Pipeline** | yt-dlp, subprocess, sqlite3 |
| **Signal Processing** | NumPy, SciPy, custom EMA smoothing |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          BROWSER (Participant)                      │
│  ┌──────────────┐    ┌──────────────────────────────────────────┐   │
│  │ Registration  │───▶│  YouTube IFrame Player (playlist mode)   │   │
│  │    Form       │    │  Reports video_id + timestamp every 200ms│   │
│  └──────────────┘    └──────────────┬───────────────────────────┘   │
└─────────────────────────────────────┼───────────────────────────────┘
                                      │ HTTP POST /status
                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FLASK SERVER (Background Thread)                │
│  Routes: / (form), /start, /status, /admin/*                       │
│  Shares STATE dict with main loop                                   │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │ Shared STATE dict
                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        MAIN LOOP (main.py)                          │
│                                                                     │
│  ┌─────────────┐   ┌──────────────────┐   ┌───────────────────┐    │
│  │  FaceTracker │   │ FacialFeature    │   │   YamnetAudio     │    │
│  │  (MediaPipe) │──▶│ Extractor        │   │   (background     │    │
│  │  Webcam      │   │ AU25, AU12, AU6  │   │    thread)        │    │
│  └─────────────┘   └───────┬──────────┘   └────────┬──────────┘    │
│                             │                       │               │
│                             ▼                       ▼               │
│                    ┌─────────────────────────────────────┐          │
│                    │         EMA Smoothers (×4)          │          │
│                    └──────────────┬──────────────────────┘          │
│                                   ▼                                 │
│                    ┌─────────────────────────────────┐              │
│                    │      AmusementScorer            │              │
│                    │  Smile / Laughter / Amusement   │              │
│                    └──────────┬──────────────────────┘              │
│                               │                                     │
│              ┌────────────────┼────────────────┐                   │
│              ▼                ▼                ▼                    │
│      ┌─────────────┐  ┌────────────┐  ┌──────────────┐            │
│      │  TextLogger  │  │  SQLite DB │  │ Debug Overlay│            │
│      │  (CSV logs)  │  │  (ORM)     │  │ (OpenCV)     │            │
│      └─────────────┘  └────────────┘  └──────────────┘            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Experiment Flow

### Phase 1 — Content Curation

1. **Video harvesting**: An automated pipeline (`harvest_to_db.py`) searches YouTube via `yt-dlp` across 7 humor categories — animals, fails, pranks, memes, reaction humor, AI-powered comedy, and Romanian humor. Up to 300 short-form videos (5–70s) per category are collected and stored in the database.
2. **Researcher review**: A password-protected admin panel lets researchers watch each harvested video and mark it as **approved** or **denied**. The workload can be split between two reviewers (odd/even rowid parity) so they work in parallel without overlap.

### Phase 2 — Running an Experiment Session

1. The researcher launches the application. A **randomized ~7-minute playlist** is assembled from the approved video pool.
2. A **Flask web server** starts and the browser opens to a participant registration form.
3. The participant enters their name/ID, age, and gender, then clicks **Start Experiment**.
4. The **YouTube player** loads and begins the playlist. Simultaneously, the backend main loop:
   - Captures **webcam frames** and runs MediaPipe face landmark detection.
   - Extracts **facial action units** (AU25, AU12, AU6) with automatic neutral-face baseline calibration.
   - Captures **microphone audio** on a background thread and classifies laughter probability via YAMNet.
   - **Smooths** all four signals with EMA filters and computes **Smile**, **Laughter**, and **Amusement** scores every frame.
   - **Logs** per-frame data (timestamp, video ID, AU values, scores) to a CSV file.
   - Tracks which video is playing and **saves per-video mean amusement scores** to the database when videos transition.
5. When the playlist ends, the browser shows "Session Complete" and the app finalizes the experiment — computing the overall session score and persisting it.

### Phase 3 — Analysis

- The SQLite database enables structured queries comparing amusement scores across subjects, individual videos, humor categories, and participant demographics.
- Per-frame CSV logs allow fine-grained temporal analysis — e.g., identifying exact moments of peak amusement within a video.

---

## Scoring Model

### Raw Signals

| Signal | Source | Computation |
|---|---|---|
| **AU25** (Mouth Openness) | Face landmarks | `lip_gap / mouth_width` |
| **AU12** (Lip Corner Puller) | Face landmarks | `(mouth_width − baseline_width) / baseline_width` (clamped ≥ 0) |
| **AU6** (Cheek Raiser) | Face landmarks | `(baseline_eye_opening − eye_opening) / baseline_eye_opening` (clamped ≥ 0) |
| **Audio** | YAMNet microphone | `P(Laughter) + P(Giggle) + P(Chuckle)` (clamped to [0, 1]) |

All signals pass through an EMA smoother: $s_t = \alpha \cdot x_t + (1 - \alpha) \cdot s_{t-1}$ with $\alpha = 0.3$.

### Composite Scores

$$\text{Smile} = 0.5 \times \text{AU12} + 0.5 \times \text{AU6}$$

$$\text{Laughter} = 0.3 \times \text{AU12} + 0.3 \times \text{AU6} + 0.2 \times \text{AU25} + 0.2 \times \text{Audio}$$

$$\text{Amusement} = 0.6 \times \text{Laughter} + 0.4 \times \text{Smile}$$

**Amusement** is the primary metric. Per-video scores are the mean of all per-frame values while that video was playing. The session total is the mean across the entire session.

---

## Database

The database stores **1,975 harvested videos** across 7 categories, **30 experiment subjects**, **30 completed experiments**, and **453 per-video amusement scores**.

---

## How to Run

### Prerequisites

- **Python 3.10–3.12** (TensorFlow requires ≤3.12)
- **Webcam** and **microphone**
- **Internet connection** (videos stream from YouTube)
- macOS or Linux (tested on macOS Apple Silicon)

### Quick Start

```bash
# The included launcher script handles everything:
./run.sh
```

The script automatically finds a compatible Python version, creates a virtual environment, installs all dependencies, runs pre-flight checks, and launches the application.

### Manual Setup

```bash
# 1. Create a virtual environment
python3.12 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt
pip install sounddevice

# 3. Run the application
cd app
python main.py
```

The web interface opens at `http://127.0.0.1:5050`. Register a participant, and the experiment begins.

---

## Project Structure

```
Laughter_Detection_Project/
├── README.md                          ← This file
├── requirements.txt                   ← Python dependencies
├── run.sh                             ← One-command launcher script
├── DOCUMENTS/
│   ├── Amusement-Research-Project.pdf ← Project presentation
│   └── Database_Schema.png            ← Visual DB schema
└── app/
    ├── main.py                        ← Entry point & real-time main loop
    ├── harvest_to_db.py               ← Automated yt-dlp video harvester
    ├── inspect_db.py                  ← Database inspector utility
    ├── app.db                         ← SQLite database
    │
    ├── audio/
    │   └── yamnet_audio.py            ← YAMNet TFLite audio classification (background thread)
    │
    ├── face/
    │   ├── face_tracker.py            ← MediaPipe FaceLandmarker webcam tracker
    │   └── facial_features.py         ← AU25/AU12/AU6 extraction + baseline calibration
    │
    ├── scoring/
    │   └── scorer.py                  ← Weighted fusion → Smile / Laughter / Amusement
    │
    ├── utils/
    │   ├── smoothing.py               ← EMA smoother
    │   └── geometry.py                ← Euclidean distance & eye aperture helpers
    │
    ├── ui/
    │   ├── overlay.py                 ← Score text overlay (OpenCV)
    │   └── au_debug_overlay.py        ← AU bar-gauge debug overlay (OpenCV)
    │
    ├── logger/
    │   └── text_logger.py             ← Per-frame CSV logger
    │
    ├── persistence/
    │   ├── db.py                      ← SQLAlchemy engine & session factory
    │   ├── models.py                  ← ORM models (Subject, Experiment, Video, Category, etc.)
    │   └── repo.py                    ← Repository functions (CRUD for experiments)
    │
    ├── playlist/
    │   └── manager.py                 ← Random playlist builder (~7 min from approved videos)
    │
    ├── web/
    │   ├── server.py                  ← Flask server (experiment + admin routes)
    │   └── templates/
    │       ├── form.html              ← Participant registration form
    │       └── player.html            ← YouTube IFrame API playlist player
    │
    ├── models/
    │   ├── face_landmarker.task       ← MediaPipe face landmark model (3.6 MB)
    │   └── yamnet.tflite              ← YAMNet audio classification model (15.3 MB)
    │
    └── logs/
        └── log.txt                    ← Session log output
```

---

## Documents

- [Project Presentation (PDF)](DOCUMENTS/Amusement-Research-Project.pdf)
- [Database Schema Diagram](DOCUMENTS/Database_Schema.png)
