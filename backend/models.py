from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.sql import func
from database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id            = Column(Integer, primary_key=True, index=True)
    filename      = Column(String, nullable=False)
    mood          = Column(String, nullable=False)
    confidence    = Column(Float, nullable=False)
    prob_happy    = Column(Float, default=0.0)
    prob_energetic = Column(Float, default=0.0)
    prob_angry    = Column(Float, default=0.0)
    prob_sad      = Column(Float, default=0.0)
    prob_relaxed  = Column(Float, default=0.0)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


class FeedbackLog(Base):
    """Stores each individual feedback event for analysis / model retraining."""
    __tablename__ = "feedback_log"

    id            = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, nullable=False, index=True)
    predicted_mood = Column(String, nullable=False)
    correct       = Column(Boolean, nullable=False)
    corrected_mood = Column(String, nullable=True)  # what user says it should be
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


# ─── Dimensional-emotion engine: analyses + human-in-the-loop feedback ───────────

class MoodAnalysis(Base):
    """One CLAP valence/arousal analysis. The stored embedding makes each row a
    potential training example once a human confirms or corrects the label —
    this is what turns usage into a growing, proprietary labelled dataset."""
    __tablename__ = "mood_analyses"

    id          = Column(Integer, primary_key=True, index=True)
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
