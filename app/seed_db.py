from persistence.db import engine, SessionLocal
from persistence.models import Base, Video, Category

# --- 1) Define your seed data here ---
# categories should match what you decided earlier
SEED_VIDEOS = [
    {
        "vid": "wqMQNIlzdGk",
        "link": "https://www.youtube.com/watch?v=wqMQNIlzdGk",
        "duration": 24,
        "categories": ["Trending Memes"]
    },
    {
        "vid": "dGU5_UUalPA",
        "link": "https://www.youtube.com/watch?v=dGU5_UUalPA",
        "duration": 95,
        "categories": ["Human Fails"]
    },
    {
        "vid": "cib8ol7OVR4",
        "link": "https://www.youtube.com/watch?v=cib8ol7OVR4",
        "duration": 9,
        "categories": ["Funny Animal Clips"]
    },
    {
        "vid": "g5PtALFhFK8",
        "link": "https://www.youtube.com/watch?v=g5PtALFhFK8",
        "duration": 301,
        "categories": ["Silent Physical Comedy"]
    },
]

def get_or_create_category(db, name: str) -> Category:
    cat = db.query(Category).filter(Category.name == name).first()
    if cat is None:
        cat = Category(name=name)
        db.add(cat)
        db.flush()
    return cat

def main():
    # Create tables if not existing
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        for item in SEED_VIDEOS:
            vid = item["vid"]

            video = db.query(Video).filter(Video.vid == vid).first()
            if video is None:
                video = Video(
                    vid=vid,
                    link=item["link"],
                    duration=item["duration"]
                )
                db.add(video)
                db.flush()

            # attach categories
            for cname in item.get("categories", []):
                cat = get_or_create_category(db, cname)
                if cat not in video.categories:
                    video.categories.append(cat)

        db.commit()
        print("✅ Seeding complete.")
    finally:
        db.close()

if __name__ == "__main__":
    main()