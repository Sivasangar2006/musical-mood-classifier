import os
import sys
import json
import uuid
import tempfile
import httpx
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

# Make the src/ package importable (the CLAP engine lives in src/emotion).
sys.path.append(str(Path(__file__).parent.parent / "src"))

from database import engine, get_db, Base
import models  # registers the SQLAlchemy models
from schemas import (
    AnalyzeResponse, AnalyzeTrackRequest, MoodFeedbackRequest,
    GoogleAuthRequest, UserOut,
)
from auth import (
    verify_google_credential, upsert_user, create_app_token,
    get_current_user, get_optional_user,
)

# CLAP valence/arousal engine. Loaded opportunistically — if torch/transformers or
# the trained head are missing, the engine is disabled and its routes return 503.
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

@app.get("/healthz")
def healthz():
    """Health check. (Root '/' is reserved for the served frontend.)"""
    return {"status": "ok", "va_engine": _va_available, "corpus": _rec_available}


# ─────────────────────────────────────────────
# Auth (Google sign-in)
# ─────────────────────────────────────────────

@app.post("/auth/google")
def auth_google(req: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Exchange a Google ID token for an app session JWT."""
    claims = verify_google_credential(req.credential)
    user = upsert_user(db, claims)
    token = create_app_token(user)
    return {"token": token, "user": UserOut.model_validate(user)}


@app.get("/auth/me", response_model=UserOut)
def auth_me(user=Depends(get_current_user)):
    """Return the currently authenticated user (401 if not signed in)."""
    return user


# ─────────────────────────────────────────────
# Dimensional-emotion (CLAP valence/arousal) endpoints
# ─────────────────────────────────────────────

def _persist_analysis(db: Session, result: dict, source_type: str,
                      title: str | None = None, artist: str | None = None,
                      user_id: int | None = None) -> int | None:
    """Save the analysis (with its embedding) so it can later be confirmed/corrected
    and become a training example. Returns the new row id, or None if the DB write
    fails (analysis still succeeds — persistence is best-effort)."""
    try:
        rec = models.MoodAnalysis(
            user_id=user_id,
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


# ─────────────────────────────────────────────
# Upload security: accept ONLY real audio, size-capped, with no user-controlled
# file paths and no arbitrary server-side fetches.
# ─────────────────────────────────────────────

_AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".mp4", ".aac", ".flac", ".ogg", ".oga", ".opus"}
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB
# Apple's preview CDN — the only hosts /analyze/track may fetch (anti-SSRF).
_ALLOWED_PREVIEW_HOSTS = (".apple.com", ".mzstatic.com")


def _looks_like_audio(head: bytes) -> bool:
    """Sniff the file signature so a renamed .txt/.json/script can't pass the
    extension check. Covers mp3, wav, flac, ogg/opus and the mp4/m4a/aac family."""
    if head[:3] == b"ID3":                                               return True  # mp3 + ID3
    if head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"\xff\xe3"):  return True  # mp3 frame
    if head[:2] in (b"\xff\xf1", b"\xff\xf9"):                           return True  # AAC (ADTS)
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":                    return True  # wav
    if head[:4] == b"fLaC":                                              return True  # flac
    if head[:4] == b"OggS":                                              return True  # ogg / opus
    if head[4:8] == b"ftyp":                                             return True  # mp4 / m4a / aac
    return False


async def _save_validated_upload(file: UploadFile) -> tuple[str, str]:
    """Validate an upload is genuine audio and write it to a server-named temp path.
    Returns (temp_path, safe_title); raises 4xx on anything that isn't clean audio."""
    name = os.path.basename(file.filename or "clip")          # strip any path components
    ext = os.path.splitext(name)[1].lower()
    if ext not in _AUDIO_EXTS:
        raise HTTPException(status_code=415,
                            detail="Unsupported file type. Upload audio (mp3, wav, m4a, flac, ogg).")
    data = await file.read(_MAX_UPLOAD_BYTES + 1)             # hard size cap before touching disk
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 20 MB).")
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    if not _looks_like_audio(data[:16]):                     # content sniff, not just extension
        raise HTTPException(status_code=415, detail="That file isn't a valid audio file.")
    temp_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}{ext}")  # never the user's name
    with open(temp_path, "wb") as buf:
        buf.write(data)
    return temp_path, name


def _validate_preview_url(url: str) -> None:
    """Anti-SSRF: /analyze/track may only fetch Apple's https preview CDN, never an
    arbitrary or internal URL."""
    p = urlparse(url)
    host = (p.hostname or "").lower()
    if p.scheme != "https" or not any(host == h.lstrip(".") or host.endswith(h)
                                      for h in _ALLOWED_PREVIEW_HOSTS):
        raise HTTPException(status_code=400, detail="preview_url must be an Apple preview https URL.")


@app.post("/analyze/upload", response_model=AnalyzeResponse)
async def analyze_upload(file: UploadFile = File(...), db: Session = Depends(get_db),
                         user=Depends(get_optional_user)):
    """Analyse an uploaded audio file's emotion with the CLAP valence/arousal engine."""
    if not _va_available:
        raise HTTPException(status_code=503, detail="CLAP V/A engine not available")

    temp_filename, title = await _save_validated_upload(file)
    try:
        result = _va_analyze(temp_filename)
        analysis_id = _persist_analysis(db, result, "upload", title=title,
                                        user_id=user.id if user else None)
        return _va_to_response(result, title=title, analysis_id=analysis_id)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)


@app.post("/analyze/track", response_model=AnalyzeResponse)
async def analyze_track(req: AnalyzeTrackRequest, db: Session = Depends(get_db),
                        user=Depends(get_optional_user)):
    """Analyse an iTunes track by its 30 s preview URL (the core product flow)."""
    if not _va_available:
        raise HTTPException(status_code=503, detail="CLAP V/A engine not available")
    if not req.preview_url:
        raise HTTPException(status_code=400, detail="preview_url is required")
    _validate_preview_url(req.preview_url)

    temp_filename = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.m4a")
    try:
        # No redirects (a redirect could escape the host allow-list); cap the body size.
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client:
            resp = await client.get(req.preview_url)
            resp.raise_for_status()
            if len(resp.content) > _MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="Preview too large.")
            with open(temp_filename, "wb") as buf:
                buf.write(resp.content)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch preview: {e}")

    try:
        result = _va_analyze(temp_filename)
        analysis_id = _persist_analysis(db, result, "track", title=req.title, artist=req.artist,
                                        user_id=user.id if user else None)
        return _va_to_response(result, title=req.title, artist=req.artist, analysis_id=analysis_id)
    except HTTPException:
        raise
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
def va_history(limit: int = Query(default=20, ge=1, le=100),
               db: Session = Depends(get_db), user=Depends(get_current_user)):
    """The signed-in user's analysed songs with mood + confidence + feedback status.
    The active, personalised replacement for the old passive history list."""
    rows = (
        db.query(models.MoodAnalysis)
        .filter(models.MoodAnalysis.user_id == user.id)
        .order_by(models.MoodAnalysis.created_at.desc())
        .limit(limit)
        .all()
    )
    ids = [r.id for r in rows]
    fb = {f.analysis_id: f for f in
          db.query(models.MoodFeedback).filter(models.MoodFeedback.analysis_id.in_(ids)).all()} if ids else {}
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
    total = db.query(models.MoodAnalysis).filter(models.MoodAnalysis.user_id == user.id).count()
    return {"total": total, "analyses": items}


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


# ─────────────────────────────────────────────
# Serve the built frontend (single-container deploy, e.g. Hugging Face Spaces).
# Mounted LAST so it only catches paths not handled by an API route above.
# No-op in local dev when the frontend hasn't been built into ./static.
# ─────────────────────────────────────────────
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_STATIC_DIR):
    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
