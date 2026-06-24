"""Continual learning: fold user feedback back into the valence/arousal head.

This closes the human-in-the-loop: every confirmation/correction collected via
/va/feedback becomes a labelled training example. We refit the regression head on
DEAM PLUS those examples (human labels upweighted), so the model improves on the
exact songs real users care about — including out-of-distribution music DEAM lacks.

Run periodically (cron) or on demand:
    python backend/retrain_from_feedback.py

It backs up the current head to va_head.joblib.bak before writing the new one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import joblib
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# backend/ imports (DB) + src/ imports (none needed here, but keep path consistent)
sys.path.append(str(Path(__file__).parent.parent / "src"))
from database import SessionLocal  # noqa: E402
import models  # noqa: E402

_ROOT = Path(__file__).parent.parent
DEAM = _ROOT / "artifacts" / "deam" / "deam_clap.npz"
HEAD = _ROOT / "artifacts" / "deam" / "va_head.joblib"
REPLICATE = 5  # upweight human-labelled examples vs the ~1800 DEAM clips


def collect_feedback() -> tuple[np.ndarray, np.ndarray]:
    """Build (embedding, [valence, arousal]) pairs from feedback joined to analyses."""
    db = SessionLocal()
    try:
        rows = (
            db.query(models.MoodFeedback, models.MoodAnalysis)
            .join(models.MoodAnalysis, models.MoodFeedback.analysis_id == models.MoodAnalysis.id)
            .all()
        )
    finally:
        db.close()

    X, y = [], []
    for fb, an in rows:
        if not an.embedding:
            continue
        emb = np.asarray(json.loads(an.embedding), dtype=np.float32)
        if fb.correct:
            tv, ta = an.valence, an.arousal              # confirmed -> own label
        else:
            tv = fb.corrected_valence if fb.corrected_valence is not None else an.valence
            ta = fb.corrected_arousal if fb.corrected_arousal is not None else an.arousal
        X.append(emb)
        y.append([tv, ta])
    if not X:
        return np.empty((0, 512), np.float32), np.empty((0, 2), np.float32)
    return np.asarray(X, np.float32), np.asarray(y, np.float32)


def main() -> None:
    if not DEAM.is_file():
        raise SystemExit(f"DEAM embeddings missing at {DEAM}")
    d = np.load(DEAM)
    Xd, yd = d["X"], np.stack([d["valence"], d["arousal"]], axis=1)

    Xf, yf = collect_feedback()
    print(f"Collected {len(Xf)} human-labelled examples.")
    if len(Xf):
        Xf_rep = np.repeat(Xf, REPLICATE, axis=0)
        yf_rep = np.repeat(yf, REPLICATE, axis=0)
        X = np.vstack([Xd, Xf_rep])
        y = np.vstack([yd, yf_rep])
    else:
        print("No feedback yet — retraining on DEAM only (no-op refit).")
        X, y = Xd, yd

    model = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 4, 25)))
    model.fit(X, y)

    if HEAD.is_file():
        HEAD.replace(HEAD.with_suffix(".joblib.bak"))
    joblib.dump({"model": model, "axes": ["valence", "arousal"], "embed": "clap-htsat-unfused"}, HEAD)
    print(f"Retrained on {len(X)} examples ({len(Xd)} DEAM + {len(Xf)}×{REPLICATE} feedback) -> {HEAD}")


if __name__ == "__main__":
    main()
