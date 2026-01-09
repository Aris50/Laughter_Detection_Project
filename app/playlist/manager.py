import random
from persistence.db import SessionLocal
from persistence.models import Video

# ================= CONFIG =================

TARGET_DURATION = 7 * 60        # 7 minutes
MAX_OVERAGE = 30               # allow +30s

# REVIEWER SPLIT
# True  -> odd IDs
# False -> even IDs
USE_ODD_IDS = True

# =========================================

def get_random_playlist():
    db = SessionLocal()
    try:
        query = (
            db.query(Video)
            .filter(Video.status == "approved")
        )

        # Even / odd split (SQLite compatible)
        if USE_ODD_IDS:
            query = query.filter(Video.vid % 2 == 1)
        else:
            query = query.filter(Video.vid % 2 == 0)

        videos = query.all()

        pool = [
            {"id": v.vid, "duration": v.duration}
            for v in videos
            if v.duration is not None
        ]

    finally:
        db.close()

    random.shuffle(pool)

    playlist = []
    total_duration = 0

    for video in pool:
        if total_duration + video["duration"] <= TARGET_DURATION + MAX_OVERAGE:
            playlist.append(video["id"])
            total_duration += video["duration"]

        if total_duration >= TARGET_DURATION:
            break

    return playlist