from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class PredictResponse(BaseModel):
    """
    This is what FastAPI sends BACK to the React frontend after analyzing a song.
    
    The frontend JavaScript will receive a JSON object with exactly these fields.
    Pydantic validates that your backend always returns data in this shape.
    """
    mood: str                    # e.g., "Happy"
    confidence: float            # e.g., 0.87
    probabilities: dict          # e.g., {"Happy": 0.87, "Sad": 0.03, ...}
    mood_emoji: str              # e.g., "😊"
    mood_description: str        # e.g., "Bright, upbeat, positive"
    prediction_id: int           # The database ID of this prediction


class PredictionRecord(BaseModel):
    """
    This represents a single prediction record as stored in the database.
    Used when returning prediction history.
    """
    id: int
    filename: str
    mood: str
    confidence: float
    prob_happy: float
    prob_energetic: float
    prob_angry: float
    prob_sad: float
    prob_relaxed: float
    created_at: datetime

    class Config:
        # This tells Pydantic to read data from SQLAlchemy model attributes
        # Without this, Pydantic wouldn't know how to read SQLAlchemy objects
        from_attributes = True


class HistoryResponse(BaseModel):
    """
    Wraps a list of prediction records with a total count.
    Returned by the GET /history endpoint.
    """
    total: int
    predictions: list[PredictionRecord]
