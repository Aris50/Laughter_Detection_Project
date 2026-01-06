import random
from persistence.db import SessionLocal
from persistence.models import Video

TARGET_DURATION = 7 * 60
MAX_OVERAGE = 30  # allow +30s

def get_random_playlist():
    db = SessionLocal()
    try:
        videos = db.query(Video).all()
        pool = [{"id": v.vid, "duration": v.duration} for v in videos]
    finally:
        db.close()

    random.shuffle(pool)

    playlist = []
    total = 0

    for v in pool:
        if total + v["duration"] <= TARGET_DURATION + MAX_OVERAGE:
            playlist.append(v["id"])
            total += v["duration"]

    return playlist