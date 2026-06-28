from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.sql import func
from database import Base


# ─── Users (Google OAuth) ────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    google_sub = Column(String, unique=True, index=True, nullable=False)  # Google's stable user id
    email      = Column(String, index=True)
    name       = Column(String, nullable=True)
    picture    = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ─── Dimensional-emotion engine: analyses + human-in-the-loop feedback ───────────

class MoodAnalysis(Base):
    """One CLAP valence/arousal analysis. The stored embedding makes each row a
    potential training example once a human confirms or corrects the label —
    this is what turns usage into a growing, proprietary labelled dataset."""
    __tablename__ = "mood_analyses"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, index=True, nullable=True)   # null = anonymous
    source_type = Column(String, default="track")   # "track" | "upload"
    title       = Column(String, nullable=True)
    artist      = Column(String, nullable=True)
    valence     = Column(Float, nullable=False)       # normalised [-1, 1]
    arousal     = Column(Float, nullable=False)
    mood        = Column(String, nullable=False)
    quadrant    = Column(String, nullable=False)
    confidence  = Column(Float, nullable=False)
    aggression  = Column(Float, default=0.0)
    embedding   = Column(Text, nullable=True)         # JSON list[512] for retraining
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


class MoodFeedback(Base):
    """A user's verdict on an analysis. `correct=True` confirms the predicted point
    as a label; a correction supplies the true mood (and/or an exact V/A point).
    Both feed the continual-learning retrain (see backend/retrain_from_feedback.py)."""
    __tablename__ = "mood_feedback"

    id                = Column(Integer, primary_key=True, index=True)
    analysis_id       = Column(Integer, nullable=False, index=True)
    correct           = Column(Boolean, nullable=False)
    corrected_mood    = Column(String, nullable=True)
    corrected_valence = Column(Float, nullable=True)   # if the user repositions the point
    corrected_arousal = Column(Float, nullable=True)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
