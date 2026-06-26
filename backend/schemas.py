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


class AnalyzeResponse(BaseModel):
    """
    Dimensional-emotion reading from the CLAP valence/arousal engine.
    Returned by the /analyze/* endpoints.

    valence/arousal are normalised to [-1, 1] (0 = neutral) for plotting on the
    circumplex; *_raw are the interpretable 1-9 values. `mood` is the nearest of
    the five product moods; `quadrant` names the emotion region.
    """
    valence: float
    arousal: float
    valence_raw: float
    arousal_raw: float
    mood: str
    quadrant: str
    confidence: float
    n_segments: int
    mood_emoji: str
    mood_description: str
    # Echoed track metadata (present when analysing an iTunes selection)
    title: Optional[str] = None
    artist: Optional[str] = None
    # Recognizable corpus songs that "feel like" this one (cosine-nearest neighbours)
    similar: list = []
    # DB id of the persisted analysis — used to attach human feedback
    analysis_id: Optional[int] = None


class AnalyzeTrackRequest(BaseModel):
    """Body for POST /analyze/track — analyse an iTunes preview by URL."""
    preview_url: str
    title: Optional[str] = None
    artist: Optional[str] = None


class GoogleAuthRequest(BaseModel):
    """Body for POST /auth/google — the Google ID token from the sign-in button."""
    credential: str


class UserOut(BaseModel):
    """Public user profile returned after login / from /auth/me."""
    id: int
    email: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None

    class Config:
        from_attributes = True


class MoodFeedbackRequest(BaseModel):
    """Body for POST /va/feedback/{analysis_id}.
    correct=True confirms the prediction; otherwise supply corrected_mood and/or an
    exact corrected valence/arousal point."""
    correct: bool
    corrected_mood: Optional[str] = None
    corrected_valence: Optional[float] = None
    corrected_arousal: Optional[float] = None
