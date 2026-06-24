import os
import sys
import json
import uuid
import shutil
import tempfile
import joblib
import numpy as np
import httpx
from sqlalchemy import Integer as SAInteger
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Add the src/ directory to the Python path so we can import extract.py
# Path(__file__) = backend/main.py
# .parent = backend/
# .parent = moodclassification/ (project root)
sys.path.append(str(Path(__file__).parent.parent / "src"))

# Now we can import your existing feature extraction code!
from extract import extract_features

try:
    import cnn_inference
    _cnn_module_available = True
except ImportError:
    _cnn_module_available = False
    print("[INFO] torch/faiss not installed — CNN endpoints disabled")

# Import our database setup
from database import engine, get_db, Base
import models  # This import triggers SQLAlchemy to register the models
from schemas import (
    PredictResponse, HistoryResponse, PredictionRecord,
    AnalyzeResponse, AnalyzeTrackRequest, MoodFeedbackRequest,
)

# CLAP valence/arousal engine (the redesign). Loaded opportunistically — if torch/
# transformers or the trained head are missing, the legacy SVM path still works.
try:
    from emotion.predict_va import analyze_audio as _va_analyze
    _va_available = True
except Exception as e:  # noqa: BLE001 — any import/load failure should just disable it
    _va_available = False
    print(f"[INFO] CLAP V/A engine disabled: {e}")

# Recommendation engine over the precomputed iTunes corpus (in-memory cosine search).
try:
    from emotion.recommend import recommend_similar, recommend_by_mood, recommend_by_text, CORPUS_NPZ
    _rec_available = CORPUS_NPZ.is_file()
except Exception as e:  # noqa: BLE001
    _rec_available = False
    print(f"[INFO] Recommendation engine disabled: {e}")

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
    print("[OK] SVM models loaded successfully")
except Exception as e:
    print(f"[ERROR] Error loading SVM models: {e}")
    raise RuntimeError(f"Could not load ML models: {e}")

# CNN + FAISS — loaded opportunistically; SVM still works if these are absent
if _cnn_module_available:
    _cnn_available   = cnn_inference.load_cnn()
    _faiss_available = cnn_inference.load_faiss()
    if _cnn_available:
        print(f"[OK] CNN model loaded  (FAISS: {_faiss_available})")
    else:
        print("[INFO] CNN model not found — CNN endpoints will return 503")
else:
    _cnn_available   = False
    _faiss_available = False

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
    temp_filename = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}_{file.filename}")
    
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


@app.post("/predict/cnn")
async def predict_mood_cnn(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    CNN-based mood prediction using mel spectrogram + ResNet18.
    Also returns top-5 similar songs from the FAISS index.
    """
    if not _cnn_available:
        raise HTTPException(
            status_code=503,
            detail="CNN model not available — train it first with src/train_cnn.py"
        )

    allowed_types = ["audio/wav", "audio/mpeg", "audio/mp3", "audio/x-wav"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Invalid file type: {file.content_type}")

    temp_filename = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}_{file.filename}")
    try:
        with open(temp_filename, "wb") as buf:
            shutil.copyfileobj(file.file, buf)

        result = cnn_inference.predict_cnn(temp_filename)
        similar = cnn_inference.find_similar(result["embedding"], k=5) if _faiss_available else []

        # Save to DB (reuse same Prediction table)
        db_prediction = models.Prediction(
            filename=file.filename,
            mood=result["mood"],
            confidence=result["confidence"],
            prob_happy=result["probabilities"].get("Happy", 0.0),
            prob_energetic=result["probabilities"].get("Energetic", 0.0),
            prob_angry=result["probabilities"].get("Angry", 0.0),
            prob_sad=result["probabilities"].get("Sad", 0.0),
            prob_relaxed=result["probabilities"].get("Relaxed", 0.0),
        )
        db.add(db_prediction)
        db.commit()
        db.refresh(db_prediction)

        return {
            "mood":          result["mood"],
            "confidence":    result["confidence"],
            "probabilities": result["probabilities"],
            "mood_emoji":    result.get("emoji", "🎵"),
            "mood_description": result.get("description", ""),
            "model":         "cnn",
            "similar_songs": similar,
            "prediction_id": db_prediction.id,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CNN analysis failed: {str(e)}")
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)


@app.get("/similar/{prediction_id}")
def get_similar(prediction_id: int, k: int = 5, db: Session = Depends(get_db)):
    """
    Given a prediction_id that came from /predict/cnn, re-runs FAISS search
    using the stored audio (not applicable here) — placeholder for future use.
    """
    if not _faiss_available:
        raise HTTPException(status_code=503, detail="FAISS index not available")
    return {"message": "Use /predict/cnn which returns similar_songs directly"}


@app.get("/capabilities")
def capabilities():
    """Returns which models and features are currently available."""
    return {
        "svm":     True,
        "cnn":     _cnn_available,
        "faiss":   _faiss_available,
        "clap_va": _va_available,
        "corpus":  _rec_available,
    }


# ─────────────────────────────────────────────
# Dimensional-emotion (CLAP valence/arousal) endpoints
# ─────────────────────────────────────────────

def _persist_analysis(db: Session, result: dict, source_type: str,
                      title: str | None = None, artist: str | None = None) -> int | None:
    """Save the analysis (with its embedding) so it can later be confirmed/corrected
    and become a training example. Returns the new row id, or None if the DB write
    fails (analysis still succeeds — persistence is best-effort)."""
    try:
        rec = models.MoodAnalysis(
            source_type=source_type, title=title, artist=artist,
            valence=result["valence"], arousal=result["arousal"],
            mood=result["mood"], quadrant=result["quadrant"],
            confidence=result["confidence"], aggression=result.get("aggression", 0.0),
            embedding=json.dumps(result["embedding"]),
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return rec.id
    except Exception as e:  # noqa: BLE001
        db.rollback()
        print(f"[WARN] could not persist analysis: {e}")
        return None


def _va_to_response(
    result: dict,
    title: str | None = None,
    artist: str | None = None,
    exclude_id: int | None = None,
    analysis_id: int | None = None,
) -> AnalyzeResponse:
    """Wrap analyze_audio() output in the API schema, attaching mood emoji/desc
    and recognizable 'similar songs' from the corpus (if the corpus is loaded)."""
    meta = MOOD_META.get(result["mood"], {"emoji": "🎵", "description": ""})
    similar = []
    if _rec_available:
        try:
            similar = recommend_similar(result["embedding"], k=8, exclude_id=exclude_id)
        except Exception as e:  # noqa: BLE001 — recs are a bonus, never fail the analysis
            print(f"[WARN] similar-song lookup failed: {e}")
    return AnalyzeResponse(
        valence=result["valence"],
        arousal=result["arousal"],
        valence_raw=result["valence_raw"],
        arousal_raw=result["arousal_raw"],
        mood=result["mood"],
        quadrant=result["quadrant"],
        confidence=result["confidence"],
        n_segments=result["n_segments"],
        mood_emoji=meta["emoji"],
        mood_description=meta["description"],
        title=title,
        artist=artist,
        similar=similar,
        analysis_id=analysis_id,
    )


@app.post("/analyze/upload", response_model=AnalyzeResponse)
async def analyze_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Analyse an uploaded audio file's emotion with the CLAP valence/arousal engine."""
    if not _va_available:
        raise HTTPException(status_code=503, detail="CLAP V/A engine not available")

    temp_filename = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}_{file.filename}")
    try:
        with open(temp_filename, "wb") as buf:
            shutil.copyfileobj(file.file, buf)
        result = _va_analyze(temp_filename)
        analysis_id = _persist_analysis(db, result, "upload", title=file.filename)
        return _va_to_response(result, title=file.filename, analysis_id=analysis_id)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)


@app.post("/analyze/track", response_model=AnalyzeResponse)
async def analyze_track(req: AnalyzeTrackRequest, db: Session = Depends(get_db)):
    """Analyse an iTunes track by its 30 s preview URL (the core product flow).

    Downloads the preview server-side, runs CLAP + the valence/arousal head, and
    returns the emotion reading with the track metadata echoed back.
    """
    if not _va_available:
        raise HTTPException(status_code=503, detail="CLAP V/A engine not available")
    if not req.preview_url:
        raise HTTPException(status_code=400, detail="preview_url is required")

    temp_filename = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}_preview.m4a")
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(req.preview_url)
            resp.raise_for_status()
            with open(temp_filename, "wb") as buf:
                buf.write(resp.content)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch preview: {e}")

    try:
        result = _va_analyze(temp_filename)
        analysis_id = _persist_analysis(db, result, "track", title=req.title, artist=req.artist)
        return _va_to_response(result, title=req.title, artist=req.artist, analysis_id=analysis_id)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)


@app.get("/va/recommend/{mood}")
def va_recommend_mood(mood: str, k: int = Query(default=15, ge=1, le=50)):
    """Model-based mood recommendations: corpus tracks nearest the mood's point in
    valence/arousal space. Unlike /recommendations/{mood} (live iTunes keyword
    search), these come from songs the model itself placed near that mood."""
    if not _rec_available:
        raise HTTPException(status_code=503, detail="Recommendation corpus not available")
    try:
        tracks = recommend_by_mood(mood, k=k)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"mood": mood, "source": "clap-corpus", "count": len(tracks), "tracks": tracks}


@app.get("/va/search")
def va_search_text(q: str = Query(..., min_length=2), k: int = Query(default=12, ge=1, le=50)):
    """Cross-modal text-to-mood search: describe a vibe ('rainy sunday drive') and
    get songs that sound like it, via CLAP's shared audio/text embedding space."""
    if not _rec_available:
        raise HTTPException(status_code=503, detail="Recommendation corpus not available")
    tracks = recommend_by_text(q, k=k)
    return {"query": q, "source": "clap-text", "count": len(tracks), "tracks": tracks}


# ─────────────────────────────────────────────
# Human-in-the-loop feedback (replaces passive History)
# ─────────────────────────────────────────────

@app.post("/va/feedback/{analysis_id}")
def va_feedback(analysis_id: int, req: MoodFeedbackRequest, db: Session = Depends(get_db)):
    """Record a user's verdict on an analysis. A confirmation turns the predicted
    point into a label; a correction supplies the true mood / valence-arousal. Both
    accumulate as training examples for the continual-learning retrain."""
    analysis = db.query(models.MoodAnalysis).filter(models.MoodAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    cv, ca = req.corrected_valence, req.corrected_arousal
    # If the user named a corrected mood but didn't drag the point, use the mood's
    # circumplex anchor as the target coordinates.
    if not req.correct and req.corrected_mood and cv is None:
        try:
            from emotion.predict_va import MOOD_ANCHORS
            if req.corrected_mood in MOOD_ANCHORS:
                cv, ca = MOOD_ANCHORS[req.corrected_mood]
        except Exception:  # noqa: BLE001
            pass

    db.add(models.MoodFeedback(
        analysis_id=analysis_id,
        correct=req.correct,
        corrected_mood=req.corrected_mood,
        corrected_valence=cv,
        corrected_arousal=ca,
    ))
    db.commit()
    return {"status": "ok", "analysis_id": analysis_id, "correct": req.correct}


@app.get("/va/history")
def va_history(limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)):
    """Recent analyses with their feedback status — the active replacement for the
    old passive history list."""
    rows = (
        db.query(models.MoodAnalysis)
        .order_by(models.MoodAnalysis.created_at.desc())
        .limit(limit)
        .all()
    )
    fb = {f.analysis_id: f for f in db.query(models.MoodFeedback).all()}
    items = []
    for r in rows:
        f = fb.get(r.id)
        items.append({
            "id": r.id, "title": r.title, "artist": r.artist,
            "mood": r.mood, "quadrant": r.quadrant,
            "valence": r.valence, "arousal": r.arousal,
            "confidence": r.confidence,
            "feedback": None if not f else {
                "correct": f.correct, "corrected_mood": f.corrected_mood,
            },
        })
    return {"total": db.query(models.MoodAnalysis).count(), "analyses": items}


@app.get("/va/feedback/stats")
def va_feedback_stats(db: Session = Depends(get_db)):
    """Dashboard numbers: how much the model is learning from users."""
    from sqlalchemy import func as sqlfunc

    total_analyses = db.query(models.MoodAnalysis).count()
    total_feedback = db.query(models.MoodFeedback).count()
    correct = db.query(models.MoodFeedback).filter(models.MoodFeedback.correct == True).count()  # noqa: E712
    corrections = total_feedback - correct
    return {
        "total_analyses": total_analyses,
        "total_feedback": total_feedback,
        "confirmed_correct": correct,
        "corrections": corrections,
        # every feedback row is a usable training example (confirm = own label, correct = new label)
        "labeled_examples_for_retrain": total_feedback,
        "accuracy": round(correct / total_feedback, 3) if total_feedback else None,
    }


_METRICS_PATH = Path(__file__).parent.parent / "artifacts" / "eval" / "metrics.json"


@app.get("/va/metrics")
def va_metrics():
    """Model evaluation metrics (R2/MAE/calibration/quadrant confusion) for the
    'About the model' dashboard. Generated offline by src/emotion/evaluate.py."""
    if not _METRICS_PATH.is_file():
        raise HTTPException(status_code=404, detail="Metrics not generated yet")
    return json.loads(_METRICS_PATH.read_text(encoding="utf-8"))


@app.post("/feedback/{prediction_id}")
def submit_feedback(
    prediction_id: int,
    correct: bool,
    corrected_mood: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Online feedback loop — user marks whether the prediction was correct.
    Stores feedback for future model retraining.
    """
    pred = db.query(models.Prediction).filter(models.Prediction.id == prediction_id).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")

    db.add(models.FeedbackLog(
        prediction_id=prediction_id,
        predicted_mood=pred.mood,
        correct=correct,
        corrected_mood=corrected_mood,
    ))
    db.commit()
    return {"status": "ok", "prediction_id": prediction_id, "correct": correct}


@app.get("/feedback/stats")
def feedback_stats(db: Session = Depends(get_db)):
    """Returns model accuracy based on user feedback."""
    from sqlalchemy import func

    total = db.query(models.FeedbackLog).count()
    correct = db.query(models.FeedbackLog).filter(models.FeedbackLog.correct == True).count()

    per_mood = (
        db.query(
            models.FeedbackLog.predicted_mood,
            func.count(models.FeedbackLog.id).label("total"),
            func.sum(
                models.FeedbackLog.correct.cast(SAInteger)
            ).label("correct_count"),
        )
        .group_by(models.FeedbackLog.predicted_mood)
        .all()
    )

    return {
        "total_feedback":    total,
        "overall_accuracy":  round(correct / total, 3) if total else None,
        "per_mood_accuracy": {
            row.predicted_mood: {
                "total":    row.total,
                "accuracy": round(row.correct_count / row.total, 3) if row.total else None,
            }
            for row in per_mood
        },
    }


# ─── iTunes Search API queries per mood ──────────────────────────────────────
# Rotated to give variety on "More" button clicks
_ITUNES_QUERIES = {
    "Happy":     ["happy pop hits", "feel good songs", "upbeat pop", "good vibes playlist"],
    "Energetic": ["workout hits", "pump up energy", "high energy dance", "adrenaline music"],
    "Angry":     ["heavy metal", "hard rock aggressive", "metalcore", "nu metal"],
    "Sad":       ["sad songs heartbreak", "emotional ballad", "melancholy indie", "crying songs"],
    "Relaxed":   ["chill lofi", "calm piano acoustic", "relaxing ambient", "peaceful instrumental"],
}

_ITUNES_BASE = "https://itunes.apple.com"


def _parse_itunes_track(t: dict) -> dict:
    return {
        "id":          t["trackId"],
        "title":       t["trackName"],
        "artist":      t["artistName"],
        "album":       t.get("collectionName", ""),
        "album_art":   t.get("artworkUrl100", t.get("artworkUrl60", "")),
        "preview_url": t.get("previewUrl", ""),
        "store_url":   t.get("trackViewUrl", ""),
        "duration_ms": t.get("trackTimeMillis", 0),
        "genre":       t.get("primaryGenreName", ""),
    }


@app.get("/recommendations/{mood}")
async def get_recommendations(
    mood: str,
    limit: int = Query(default=8, ge=1, le=20),
    offset: int = Query(default=0, ge=0),
):
    """
    Returns iTunes track recommendations for a given mood.
    Proxied through the backend to avoid any browser CORS issues.
    Each track includes: title, artist, album_art, preview_url (30s AAC), store_url.
    """
    queries = _ITUNES_QUERIES.get(mood)
    if not queries:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown mood: {mood}. Use one of {list(_ITUNES_QUERIES)}"
        )

    # Rotate query variant based on page number so "More" gives fresh results
    page = offset // limit
    query = queries[page % len(queries)]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{_ITUNES_BASE}/search",
                params={
                    "term":   query,
                    "media":  "music",
                    "entity": "song",
                    "limit":  limit,
                    "offset": offset % (limit * len(queries)),  # cycle within page window
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"iTunes API error: {e}")

    tracks = [
        _parse_itunes_track(t)
        for t in data.get("results", [])
        if t.get("kind") == "song" and t.get("previewUrl")
    ]

    return {
        "mood":   mood,
        "query":  query,
        "total":  data.get("resultCount", len(tracks)),
        "tracks": tracks,
    }


@app.get("/recommendations/{mood}/search")
async def search_recommendations(
    mood: str,
    q: str = Query(..., min_length=1),
    limit: int = Query(default=8, ge=1, le=20),
):
    """
    Search iTunes for any song or artist name and return results with 30s previews.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{_ITUNES_BASE}/search",
                params={"term": q, "media": "music", "entity": "song", "limit": limit},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"iTunes API error: {e}")

    tracks = [
        _parse_itunes_track(t)
        for t in data.get("results", [])
        if t.get("kind") == "song"
    ]

    return {"query": q, "mood": mood, "tracks": tracks}
