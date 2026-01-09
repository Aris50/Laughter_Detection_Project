import json
import subprocess
import time
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ======================
# CONFIG
# ======================
DB_PATH = Path(__file__).resolve().parent / "app.db"

TARGET_PER_CATEGORY = 300
RESULTS_PER_QUERY = 100
MAX_QUERIES_PER_CATEGORY = 10

MAX_DURATION_SECONDS = 70
MIN_DURATION_SECONDS = 5

SLEEP_BETWEEN_QUERIES_SEC = 0.3
COMMIT_EVERY = 25  # commit in batches (crash-safe + faster)

CATEGORY_QUERIES = {
    "pranks": [
        "awkward interactions", 
        "library prank", "shampoo prank shorts", "wholesome pranks", "invisible prank"
    ],
    "memes": [
        "brainrot memes", "shitposting status", "pov relatable", 
        "corecore", "discord memes shorts", "sigma grindset meme", 
        "subway surfers humor", "lobotomy kaisen", "corporate humor", "loud sound memes"
    ],
    "reaction_humor": [
        "streamer rage", "twitch clips funny", "ishowspeed funny moments", 
        "kai cenat clips", "ylyl shorts", "streamer jumpscare", 
        "xqc reaction", "funny mic moments", "rage quit", "laughing at memes"
    ],
    "ai_powered": [
        "ai voice trolling", "presidents gaming", "ai cover songs", 
        "cursed ai images", "weird ai commercials", "ai generated horror funny", 
        "chatgpt fails", "balenciaga meme", "ai filter funny", "deepfake meme"
    ],
    "romanian": [
        "caterinca romania", "stand up comedy romania shorts", "prajiti pe tiktok", 
        "faze comice trafic", "romania pov", "meme" 
        "manele funny", "scoala romaneasca", "vloggeri romani cringe", "haz de necaz"
    ]
}
'''
CATEGORY_QUERIES = {
    "animals": [
        "funny cat shorts", "orange cat behavior", "husky tantrums", 
        "pets interrupting work", "dog bombastic side eye", "capybara chill vibes", 
        "cat chaos", "animals acting human", "funny dog reaction", "hamster cult"
    ],
    "fails": [
        "gym fails funny", "work fails", "caught in 4k", 
        "instant karma shorts", "cooking disasters", "drunk people funny", 
        "crash out moments", "funny falls", "parkour fail", "job interview fail"
    ],
    "pranks": [
        "npc prank", "public confusion", "elevator prank", 
        "scaring streamers", "dad jokes to strangers", "awkward interactions", 
        "library prank", "shampoo prank shorts", "wholesome pranks", "invisible prank"
    ],
    "memes": [
        "brainrot memes", "shitposting status", "pov relatable", 
        "corecore", "discord memes shorts", "sigma grindset meme", 
        "subway surfers humor", "lobotomy kaisen", "corporate humor", "loud sound memes"
    ],
    "reaction_humor": [
        "streamer rage", "twitch clips funny", "ishowspeed funny moments", 
        "kai cenat clips", "ylyl shorts", "streamer jumpscare", 
        "xqc reaction", "funny mic moments", "rage quit", "laughing at memes"
    ],
    "ai_powered": [
        "ai voice trolling", "presidents gaming", "ai cover songs", 
        "cursed ai images", "weird ai commercials", "ai generated horror funny", 
        "chatgpt fails", "balenciaga meme", "ai filter funny", "deepfake meme"
    ],
    "romanian": [
        "caterinca romania", "stand up comedy romania shorts", "prajiti pe tiktok", 
        "faze comice trafic", "romania pov", "meme" 
        "manele funny", "scoala romaneasca", "vloggeri romani cringe", "haz de necaz"
    ]
}
'''

# ======================
# yt-dlp helpers
# ======================
def run_ytdlp_search(query: str) -> Tuple[List[dict], str]:
    """
    Never raises. Returns (items, stderr_tail).
    Uses --ignore-errors so age-gated/private/unavailable entries won't crash the run.
    """
    search_url = f"ytsearch{RESULTS_PER_QUERY}:{query}"
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--dump-json",
        "--ignore-errors",
        "--no-warnings",
        search_url
    ]

    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = p.communicate()
    except Exception as e:
        return [], f"Exception running yt-dlp: {e}"

    if (p.returncode != 0) and (not stdout):
        tail = "\n".join((stderr or "").strip().splitlines()[-3:])
        return [], tail

    items: List[dict] = []
    for line in (stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    tail = "\n".join((stderr or "").strip().splitlines()[-3:])
    return items, tail


def normalize(item: dict) -> Optional[Tuple[str, str, int]]:
    """
    Returns (vid, link, duration) or None if invalid/out of bounds.
    """
    vid = item.get("id")
    if not vid:
        return None

    duration = item.get("duration")
    if duration is None:
        return None

    try:
        duration = int(duration)
    except Exception:
        return None

    if MIN_DURATION_SECONDS is not None and duration < MIN_DURATION_SECONDS:
        return None
    if MAX_DURATION_SECONDS is not None and duration > MAX_DURATION_SECONDS:
        return None

    link = f"https://www.youtube.com/watch?v={vid}"
    return vid, link, duration


# ======================
# DB helpers
# ======================
def db_connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"DB not found at: {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def load_category_ids(conn: sqlite3.Connection) -> Dict[str, int]:
    """
    Category table schema: (cid, name)
    """
    rows = conn.execute("SELECT cid, name FROM Category").fetchall()
    mapping = {r["name"]: int(r["cid"]) for r in rows}

    missing = [c for c in CATEGORY_QUERIES.keys() if c not in mapping]
    if missing:
        raise RuntimeError(
            "Missing categories in DB: " + ", ".join(missing) +
            "\nInsert them into Category(name) first."
        )
    return mapping


def count_videos_for_category(conn: sqlite3.Connection, category_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM Video WHERE category_id = ?",
        (category_id,)
    ).fetchone()
    return int(row["c"])


def insert_video(
    conn: sqlite3.Connection,
    vid: str,
    link: str,
    duration: int,
    category_id: int,
    harvest_query: str
) -> bool:
    """
    Returns True if inserted, False if ignored (already exists).
    Assumes Video.vid is PRIMARY KEY or UNIQUE.
    """
    cur = conn.execute(
        """
        INSERT OR IGNORE INTO Video (vid, link, duration, status, category_id, harvest_query)
        VALUES (?, ?, ?, 'n/a', ?, ?)
        """,
        (vid, link, duration, category_id, harvest_query)
    )
    return cur.rowcount == 1


# ======================
# Main harvesting
# ======================
def main():
    conn = db_connect()
    try:
        cat_ids = load_category_ids(conn)
        inserted_since_commit = 0

        for category, queries in CATEGORY_QUERIES.items():
            category_id = cat_ids[category]

            print(f"\n=== {category} ===")
            current_count = count_videos_for_category(conn, category_id)
            print(f"  already in DB: {current_count}/{TARGET_PER_CATEGORY}")

            if current_count >= TARGET_PER_CATEGORY:
                print("  skipping (target reached)")
                continue

            for qi, q in enumerate(queries[:MAX_QUERIES_PER_CATEGORY], start=1):
                current_count = count_videos_for_category(conn, category_id)
                if current_count >= TARGET_PER_CATEGORY:
                    break

                items, err_tail = run_ytdlp_search(q)
                if not items:
                    print(
                        f"  [warn] query {qi}/{min(len(queries), MAX_QUERIES_PER_CATEGORY)} "
                        f"'{q}' -> 0 items. {err_tail}"
                    )
                    time.sleep(SLEEP_BETWEEN_QUERIES_SEC)
                    continue

                added = 0
                for item in items:
                    norm = normalize(item)
                    if not norm:
                        continue

                    vid, link, dur = norm

                    if insert_video(conn, vid, link, dur, category_id, q):
                        added += 1
                        inserted_since_commit += 1

                        if inserted_since_commit >= COMMIT_EVERY:
                            conn.commit()
                            inserted_since_commit = 0

                    current_count = count_videos_for_category(conn, category_id)
                    if current_count >= TARGET_PER_CATEGORY:
                        break

                current_count = count_videos_for_category(conn, category_id)
                print(
                    f"  query {qi}/{min(len(queries), MAX_QUERIES_PER_CATEGORY)} "
                    f"-> +{added} (now {current_count}/{TARGET_PER_CATEGORY})"
                )

                time.sleep(SLEEP_BETWEEN_QUERIES_SEC)

            conn.commit()
            print(f"  total for {category}: {count_videos_for_category(conn, category_id)}")

        conn.commit()
        print("\nDone. Videos saved into app.db (Video) with category_id + harvest_query.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()