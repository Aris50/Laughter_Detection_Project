from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy import Column, Integer, String, Float, Enum, ForeignKey, Table

class Base(DeclarativeBase):
    pass

video_category = Table(
    "VideoCategory",
    Base.metadata,
    Column("vid", String(32), ForeignKey("Video.vid", ondelete="CASCADE"), primary_key=True),
    Column("cid", Integer, ForeignKey("Category.cid", ondelete="CASCADE"), primary_key=True),
)

class Subject(Base):
    __tablename__ = "Subject"
    sid = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)

class Experiment(Base):
    __tablename__ = "Experiment"
    eid = Column(Integer, primary_key=True, autoincrement=True)
    sid = Column(Integer, ForeignKey("Subject.sid", ondelete="CASCADE"), nullable=False)
    type = Column(Enum("single", "group", name="exp_type"), nullable=False)
    total_score = Column(Float, nullable=True)

class Video(Base):
    __tablename__ = "Video"
    vid = Column(String(32), primary_key=True)  # YouTube ID (e.g., "wqMQNIlzdGk")
    link = Column(String(2048), nullable=False)
    duration = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="n/a")

    categories = relationship("Category", secondary=video_category, back_populates="videos")

class Category(Base):
    __tablename__ = "Category"
    cid = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)

    videos = relationship("Video", secondary=video_category, back_populates="categories")

class ExperimentVideo(Base):
    __tablename__ = "ExperimentVideo"
    eid = Column(Integer, ForeignKey("Experiment.eid", ondelete="CASCADE"), primary_key=True)
    vid = Column(String(32), ForeignKey("Video.vid", ondelete="CASCADE"), primary_key=True)
    score = Column(Float, nullable=True)