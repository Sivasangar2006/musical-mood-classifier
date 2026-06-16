import os
import sys
import uuid
import shutil
import joblib
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Add the src/ directory to the Python path so we can import extract.py
# Path(__file__) = backend/main.py
# .parent = backend/
# .parent = moodclassification/ (project root)
sys.path.append(str(Path(__file__).parent.parent / "src"))

# Now we can import your existing feature extraction code!
from extract import extract_features

# Import our database setup
from database import engine, get_db, Base
import models  # This import triggers SQLAlchemy to register the models
from schemas import PredictResponse, HistoryResponse, PredictionRecord

load_dotenv()

# ─────────────────────────────────────────────
# App Initialization
# ─────────────────────────────────────────────

# Create the FastAPI application
app = FastAPI(
    title="Musical Mood Classifier API",
    description="Analyzes audio files and predicts their emotional mood",
    version="1.0.0"
)

# ─────────────────────────────────────────────
# CORS Configuration
# ─────────────────────────────────────────────

# CORS (Cross-Origin Resource Sharing) is a browser security feature.
# By default, browsers block requests between different origins.
# Your React app runs on http://localhost:5173 (or 3000)
# Your FastAPI runs on http://localhost:8000
# These are DIFFERENT origins → browser would block the request.
# The code below tells FastAPI to explicitly allow requests from your React app.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Load ML Models at Startup
# ─────────────────────────────────────────────

# These are loaded ONCE when the server starts, not on every request.
# Loading .pkl files is slow (~1-2 seconds). You don't want users waiting for it.
MODEL_DIR = Path(os.getenv("MODEL_DIR", "../models"))

try:
    model = joblib.load(MODEL_DIR / "model.pkl")
    scaler = joblib.load(MODEL_DIR / "scaler.pkl")
    encoder = joblib.load(MODEL_DIR / "encoder.pkl")
    print("[OK] Models loaded successfully")
except Exception as e:
    print(f"[ERROR] Error loading models: {e}")
    raise RuntimeError(f"Could not load ML models: {e}")

# Mood metadata: emoji and description for each mood label
MOOD_META = {
    "Happy":     {"emoji": "😊", "description": "Bright, upbeat, positive"},
    "Energetic": {"emoji": "⚡", "description": "Fast, driving, full of energy"},
    "Angry":     {"emoji": "😠", "description": "Intense, aggressive, heavy"},
    "Sad":       {"emoji": "😢", "description": "Melancholic, slow, introspective"},
    "Relaxed":   {"emoji": "😌", "description": "Calm, soothing, peaceful"},
}

# ─────────────────────────────────────────────
# Database Setup
# ─────────────────────────────────────────────

# Create all tables defined in models.py if they don't already exist
# This is safe to run on every startup — it won't overwrite existing data
Base.metadata.create_all(bind=engine)


# ─────────────────────────────────────────────
# Routes (API Endpoints)
# ─────────────────────────────────────────────

@app.get("/")
def root():
    """Health check endpoint. Returns a simple message to confirm the server is running."""
    return {"status": "ok", "message": "Mood Classifier API is running"}


@app.post("/predict", response_model=PredictResponse)
async def predict_mood(
    file: UploadFile = File(...),      # The uploaded audio file
    db: Session = Depends(get_db)      # FastAPI injects a database session automatically
):
    """
    Main prediction endpoint.
    
    Accepts: A .wav or .mp3 file (multipart form data)
    Returns: Predicted mood, confidence, all probabilities, emoji, description
    
    What happens step by step:
    1. Save the uploaded file temporarily
    2. Extract 56 audio features using librosa
    3. Scale the features using the fitted StandardScaler
    4. Run the ML model to get probabilities for all 5 moods
    5. Find the highest probability → that's the predicted mood
    6. Save the result to PostgreSQL
    7. Return the result as JSON
    8. Clean up the temporary file
    """
    
    # Step 1: Validate file type
    # Only allow audio files — reject PDFs, images, etc.
    allowed_types = ["audio/wav", "audio/mpeg", "audio/mp3", "audio/x-wav"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Please upload a .wav or .mp3 file."
        )
    
    # Step 2: Save to a temporary location
    # We use uuid4() to generate a random unique filename to avoid conflicts
    # if two users upload at the same time
    temp_filename = f"/tmp/{uuid.uuid4()}_{file.filename}"
    
    try:
        # Write the uploaded bytes to disk
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Step 3: Extract audio features using your existing code
        # This returns a 1D numpy array of 56 numbers
        features = extract_features(temp_filename)
        
        if features is None:
            raise HTTPException(
                status_code=422,
                detail="Could not extract features from the audio file. Make sure it's a valid audio file."
            )
        
        # Step 4: Scale features using the same scaler that was used during training
        # The model expects features in the same scale it was trained on
        features_scaled = scaler.transform([features])
        
        # Step 5: Get probabilities for all 5 moods
        # predict_proba returns an array like [[0.87, 0.03, 0.02, 0.05, 0.03]]
        # The inner array has one probability per mood class
        proba = model.predict_proba(features_scaled)[0]  # [0] gets the first (only) sample
        
        # Get the mood labels in the same order as the probabilities
        # encoder.classes_ returns something like ['Angry', 'Energetic', 'Happy', 'Relaxed', 'Sad']
        mood_labels = list(encoder.classes_)
        
        # Build a dict: {"Angry": 0.02, "Energetic": 0.03, "Happy": 0.87, ...}
        prob_dict = {label: float(prob) for label, prob in zip(mood_labels, proba)}
        
        # The predicted mood is the one with the highest probability
        predicted_mood = max(prob_dict, key=prob_dict.get)
        confidence = prob_dict[predicted_mood]
        
        # Step 6: Save to database
        db_prediction = models.Prediction(
            filename=file.filename,
            mood=predicted_mood,
            confidence=confidence,
            prob_happy=prob_dict.get("Happy", 0.0),
            prob_energetic=prob_dict.get("Energetic", 0.0),
            prob_angry=prob_dict.get("Angry", 0.0),
            prob_sad=prob_dict.get("Sad", 0.0),
            prob_relaxed=prob_dict.get("Relaxed", 0.0),
        )
        db.add(db_prediction)
        db.commit()
        db.refresh(db_prediction)  # Refreshes the object to get the auto-assigned ID
        
        # Step 7: Build and return the response
        meta = MOOD_META.get(predicted_mood, {"emoji": "🎵", "description": ""})
        
        return PredictResponse(
            mood=predicted_mood,
            confidence=confidence,
            probabilities=prob_dict,
            mood_emoji=meta["emoji"],
            mood_description=meta["description"],
            prediction_id=db_prediction.id
        )
    
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is (they already have proper status codes)
    
    except Exception as e:
        # Catch any unexpected errors (librosa failure, model error, etc.)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    
    finally:
        # Step 8: Always clean up the temp file, even if an error occurred
        if os.path.exists(temp_filename):
            os.remove(temp_filename)


@app.get("/history", response_model=HistoryResponse)
def get_history(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Returns the most recent predictions stored in the database.
    
    Query params:
        limit: How many records to return (default: 20, max: 100)
    """
    limit = min(limit, 100)  # Cap at 100 to prevent huge responses
    
    # SQLAlchemy query:
    # SELECT * FROM predictions ORDER BY created_at DESC LIMIT {limit}
    predictions = (
        db.query(models.Prediction)
        .order_by(models.Prediction.created_at.desc())
        .limit(limit)
        .all()
    )
    
    total = db.query(models.Prediction).count()
    
    return HistoryResponse(
        total=total,
        predictions=[PredictionRecord.model_validate(p) for p in predictions]
    )


@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """
    Returns aggregated statistics about all predictions.
    Useful for a dashboard showing mood distribution.
    """
    from sqlalchemy import func
    
    # Count how many times each mood was predicted
    mood_counts = (
        db.query(models.Prediction.mood, func.count(models.Prediction.id).label("count"))
        .group_by(models.Prediction.mood)
        .all()
    )
    
    total = db.query(models.Prediction).count()
    
    return {
        "total_predictions": total,
        "mood_distribution": {row.mood: row.count for row in mood_counts}
    }
