#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  Laughter & Amusement Detection System — Launcher Script
#  Handles venv creation, dependency installation, and startup.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
APP_DIR="$PROJECT_DIR/app"
REQUIREMENTS="$PROJECT_DIR/requirements.txt"

# ── Colours ──────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Colour

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ── 1. Find a compatible Python (3.10 – 3.12) ───────────────
find_python() {
    # Prefer 3.12, then 3.11, then 3.10
    for candidate in python3.12 python3.11 python3.10; do
        if command -v "$candidate" &>/dev/null; then
            echo "$candidate"
            return
        fi
    done

    # Fall back to python3 if its version is in range
    if command -v python3 &>/dev/null; then
        local ver
        ver="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
        case "$ver" in
            3.10|3.11|3.12) echo "python3"; return ;;
        esac
    fi

    return 1
}

PYTHON="$(find_python)" || {
    error "No compatible Python found (need 3.10–3.12)."
    error "Install one with:  brew install python@3.12"
    exit 1
}

PY_VERSION="$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')"
ok "Using ${BOLD}$PYTHON${NC} (${PY_VERSION})"

# ── 2. Create virtual environment if missing ─────────────────
if [[ ! -d "$VENV_DIR" ]]; then
    info "Creating virtual environment in ${BOLD}venv/${NC} ..."
    "$PYTHON" -m venv "$VENV_DIR"
    ok "Virtual environment created."
else
    ok "Virtual environment already exists."
fi

# Activate
source "$VENV_DIR/bin/activate"
ok "Activated venv ($(python --version))"

# ── 3. Install / update dependencies ─────────────────────────
# Use a stamp file so we don't pip-install on every launch
STAMP="$VENV_DIR/.deps_installed"
if [[ ! -f "$STAMP" ]] || [[ "$REQUIREMENTS" -nt "$STAMP" ]]; then
    info "Installing dependencies from requirements.txt ..."
    pip install --upgrade pip --quiet
    pip install -r "$REQUIREMENTS" --quiet
    # sounddevice is imported but missing from requirements.txt
    pip install sounddevice --quiet 2>/dev/null || true
    touch "$STAMP"
    ok "Dependencies installed."
else
    ok "Dependencies up to date (skipping pip install)."
fi

# ── 4. Pre-flight checks ─────────────────────────────────────
echo ""
info "Running pre-flight checks ..."

# 4a. ML models
MODELS_OK=true
for model in face_landmarker.task yamnet.tflite; do
    if [[ ! -f "$APP_DIR/models/$model" ]]; then
        error "Missing model: app/models/$model"
        MODELS_OK=false
    fi
done
$MODELS_OK && ok "ML models present."

# 4b. Database
if [[ ! -f "$APP_DIR/app.db" ]]; then
    error "Database not found at app/app.db"
    error "Run the harvester first:  cd app && python harvest_to_db.py"
    exit 1
fi
ok "Database found (app/app.db)."

# 4c. Approved video count
APPROVED="$(python -c "
import sqlite3, sys
conn = sqlite3.connect('$APP_DIR/app.db')
n = conn.execute(\"SELECT COUNT(*) FROM Video WHERE status='approved'\").fetchone()[0]
print(n)
conn.close()
")"

if [[ "$APPROVED" -eq 0 ]]; then
    warn "No approved videos in the database!"
    warn "The playlist will be empty. Approve videos first via the admin panel."
    warn "  → Launch the app, then visit http://127.0.0.1:5000/admin"
    warn "  → Default password: affectivecomputing2025"
    echo ""
    read -rp "Continue anyway? [y/N] " choice
    case "$choice" in
        y|Y) info "Continuing with 0 approved videos ..." ;;
        *)   info "Exiting. Approve some videos first, then re-run."; exit 0 ;;
    esac
else
    ok "$APPROVED approved videos available for playlists."
fi

# 4d. Webcam quick check (non-blocking — just warn)
python -c "
import cv2, sys
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print('WARN')
else:
    print('OK')
cap.release()
" 2>/dev/null | {
    read -r result
    if [[ "$result" == "WARN" ]]; then
        warn "Could not open webcam (camera index 0). The app will fail at startup."
    else
        ok "Webcam accessible."
    fi
}

# ── 5. Launch ─────────────────────────────────────────────────
echo ""
echo -e "${BOLD}════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  Launching Laughter & Amusement Detection System  ${NC}"
echo -e "${BOLD}════════════════════════════════════════════════════${NC}"
echo ""
info "Web UI will open at ${BOLD}http://127.0.0.1:5050${NC}"
info "Press ${BOLD}Esc${NC} in the OpenCV window to stop early."
echo ""

cd "$APP_DIR"
exec python main.py
