from pathlib import Path

INP = "youtube_seed_fixed.sql"
OUT = "youtube_seed_ready.sql"

text = Path(INP).read_text(encoding="utf-8")

text = text.replace(
    "INSERT OR IGNORE INTO Video (youtube_id,url,duration_seconds)",
    "INSERT OR IGNORE INTO Video (vid,link,duration)"
)

Path(OUT).write_text(text, encoding="utf-8")
print("Done. Wrote youtube_seed_ready.sql")