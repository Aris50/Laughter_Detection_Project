from typing import Optional
from persistence.db import SessionLocal
from persistence.models import Subject, Experiment, Video, ExperimentVideo

def get_or_create_subject(name: str, age: Optional[int], gender: Optional[str]) -> int:
    db = SessionLocal()
    try:
        q = db.query(Subject).filter(Subject.name == name)
        if age is not None:
            q = q.filter(Subject.age == age)
        if gender is not None:
            q = q.filter(Subject.gender == gender)

        s = q.first()
        if s is None:
            s = Subject(name=name, age=age, gender=gender)
            db.add(s)
            db.commit()
            db.refresh(s)
        return s.sid
    finally:
        db.close()

def create_experiment(sid: int, exp_type: str) -> int:
    db = SessionLocal()
    try:
        e = Experiment(sid=sid, type=exp_type, total_score=None)
        db.add(e)
        db.commit()
        db.refresh(e)
        return e.eid
    finally:
        db.close()

def video_exists(vid: str) -> bool:
    db = SessionLocal()
    try:
        return db.query(Video).filter(Video.vid == vid).first() is not None
    finally:
        db.close()

def save_video_score(eid: int, vid: str, score: float) -> None:
    db = SessionLocal()
    try:
        row = ExperimentVideo(eid=eid, vid=vid, score=score)
        db.add(row)
        db.commit()
    finally:
        db.close()

def finalize_experiment(eid: int, total_score: float) -> None:
    db = SessionLocal()
    try:
        e = db.query(Experiment).filter(Experiment.eid == eid).first()
        if e:
            e.total_score = total_score
            db.commit()
    finally:
        db.close()