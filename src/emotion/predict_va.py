"""Serving: turn an audio file into a full dimensional-emotion reading.

Pipeline: audio -> CLAP embedding(s) -> valence/arousal regression head -> a point
in the circumplex, plus the nearest named mood, its quadrant, and a confidence
derived from how consistent the per-chunk predictions are over time.

This is the request-time path the /analyze endpoint calls. The heavy CLAP model is
lazy-loaded on first use (see emotion.embed) so importing this module is cheap.
"""

from __future__ import annotations

import functools
import os
from pathlib import Path

import joblib
import numpy as np

from emotion.deam import from_unit
from emotion.embed import embed_audio_full_cached as embed_audio_full
from emotion.zero_shot import correct as zs_correct

# Resolve the trained head relative to the repo root so it works regardless of the
# server's working directory (the FastAPI app runs from backend/).
_REPO_ROOT = Path(__file__).resolve().parents[2]
HEAD_PATH = Path(os.getenv("VA_HEAD", _REPO_ROOT / "artifacts" / "deam" / "va_head.joblib"))

# The five product moods placed as anchor points in normalised (valence, arousal)
# space, so a continuous prediction maps back to the UI's existing mood vocabulary.
# Russell's circumplex: x = valence (unpleasant->pleasant), y = arousal (calm->excited).
MOOD_ANCHORS = {
    "Happy":     (0.6, 0.4),
    "Energetic": (0.3, 0.8),     # energetic implies *positive* high arousal
    "Angry":     (-0.45, 0.6),   # negative-valence high arousal -> angry, not energetic
    "Sad":       (-0.6, -0.5),
    "Relaxed":   (0.55, -0.5),
}

QUADRANTS = {
    (True, True): "happy/excited",
    (True, False): "calm/content",
    (False, True): "tense/angry",
    (False, False): "sad/depressed",
}


@functools.lru_cache(maxsize=1)
def _load_head():
    if not HEAD_PATH.is_file():
        raise FileNotFoundError(
            f"Regression head not found at {HEAD_PATH}. "
            f"Run `python -m emotion.train_va` first."
        )
    return joblib.load(HEAD_PATH)


def _nearest_mood(valence: float, arousal: float) -> str:
    p = np.array([valence, arousal])
    return min(MOOD_ANCHORS, key=lambda m: np.linalg.norm(p - np.array(MOOD_ANCHORS[m])))


def analyze_audio(path: str | Path) -> dict:
    """Predict the dimensional emotion of an audio clip.

    Returns valence/arousal (both normalised [-1,1] and raw 1-9), the nearest named
    mood, the circumplex quadrant, a confidence in [0,1], and the pooled CLAP
    embedding (reused later as the query vector for recommendations).
    """
    head = _load_head()["model"]
    pooled, per_chunk = embed_audio_full(path)

    # Predict per chunk, then aggregate. Mean = the reading; spread = uncertainty.
    preds = head.predict(per_chunk)                     # (n_chunks, 2)
    mean = preds.mean(axis=0)
    std = preds.std(axis=0)

    # Zero-shot gate correction: fixes out-of-distribution music (e.g. metal) that
    # the DEAM regressor rates as falsely positive. No-op for normal music.
    corr = zs_correct(pooled, float(mean[0]), float(mean[1]))
    valence = float(np.clip(corr["valence"], -1.0, 1.0))
    arousal = float(np.clip(corr["arousal"], -1.0, 1.0))

    # Consistency: tight temporal agreement -> high. NOT a probability of the mood;
    # it measures whether the song's segments read the same way. We also discount it
    # when the zero-shot gate fired, since that flags out-of-distribution audio.
    spread = float((std[0] + std[1]) / 2.0)
    consistency = max(0.0, min(1.0, 1.0 - spread / 0.6))
    confidence = round(consistency * (1.0 - 0.3 * corr["gate"]), 3)

    return {
        "valence": round(valence, 3),
        "arousal": round(arousal, 3),
        "valence_raw": round(from_unit(valence), 2),   # back on the 1-9 scale
        "arousal_raw": round(from_unit(arousal), 2),
        "mood": _nearest_mood(valence, arousal),
        "quadrant": QUADRANTS[(valence >= 0, arousal >= 0)],
        "confidence": confidence,
        "aggression": corr["aggression"],
        "n_segments": int(per_chunk.shape[0]),
        "valence_std": round(float(std[0]), 3),
        "arousal_std": round(float(std[1]), 3),
        "embedding": pooled.astype(np.float32).tolist(),
        "model": "clap-va",
    }


if __name__ == "__main__":
    # Sanity check against a few DEAM clips with known labels.
    from emotion.deam import load_deam_manifest

    mani = load_deam_manifest().sample(3, random_state=0)
    for row in mani.itertuples(index=False):
        r = analyze_audio(row.audio_path)
        print(f"song {row.song_id}: pred V={r['valence_raw']} A={r['arousal_raw']} "
              f"({r['mood']}, {r['quadrant']}, conf={r['confidence']}) | "
              f"true V={row.valence_mean} A={row.arousal_mean}")
