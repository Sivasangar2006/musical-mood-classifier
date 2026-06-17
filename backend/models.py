from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
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
