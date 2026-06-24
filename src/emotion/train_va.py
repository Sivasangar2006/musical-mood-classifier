"""Train the valence/arousal regression head on CLAP embeddings.

This is the model that replaces the old single-label mood classifier. Instead of
predicting one of N moods, it regresses a point in the continuous valence-arousal
plane (Russell's circumplex). Moods then fall out as *regions* of that plane.

We report, on a held-out test split:
  - per-axis R2 and MAE (valence is famously harder than arousal in MIR)
  - MAE back on the interpretable raw 1-9 scale
  - quadrant accuracy: collapse (valence, arousal) signs into the 4 classic mood
    quadrants (happy / calm / sad / tense) so we have a discrete, intuitive number
  - a mean-predictor baseline, so the R2 numbers are honestly contextualised
"""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from emotion.deam import VA_SCALE_MAX, VA_SCALE_MID

DEFAULT_EMB = Path("artifacts/deam/deam_clap.npz")
DEFAULT_OUT = Path("artifacts/deam/va_head.joblib")

# Quadrant of the circumplex from (valence_sign, arousal_sign), centred at 0.
QUADRANTS = {
    (True, True): "happy/excited",     # +V +A
    (True, False): "calm/content",     # +V -A
    (False, True): "tense/angry",      # -V +A
    (False, False): "sad/depressed",   # -V -A
}


def _quadrant(valence: np.ndarray, arousal: np.ndarray) -> np.ndarray:
    return np.array([f"{v >= 0}_{a >= 0}" for v, a in zip(valence, arousal)])


def main(emb_path: Path, out_path: Path, test_size: float = 0.2, seed: int = 42) -> None:
    if not emb_path.exists():
        raise FileNotFoundError(
            f"{emb_path} not found — run `python -m emotion.build_embeddings` first."
        )
    data = np.load(emb_path)
    X = data["X"]
    y = np.stack([data["valence"], data["arousal"]], axis=1)  # normalised [-1,1]

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=test_size, random_state=seed)

    # RidgeCV picks its own alpha; StandardScaler because CLAP dims aren't unit-scaled.
    model = make_pipeline(
        StandardScaler(),
        RidgeCV(alphas=np.logspace(-2, 4, 25)),
    )
    model.fit(X_tr, y_tr)
    pred = model.predict(X_te)

    axes = ["valence", "arousal"]
    scale = VA_SCALE_MAX - VA_SCALE_MID  # 4.0: maps normalised error -> 1-9 units

    print(f"\nTrained on {len(X_tr)} clips, tested on {len(X_te)}.")
    print(f"{'axis':<10} {'R2':>7} {'MAE(norm)':>10} {'MAE(1-9)':>9} {'baselineR2':>11}")
    for i, ax in enumerate(axes):
        r2 = r2_score(y_te[:, i], pred[:, i])
        mae = mean_absolute_error(y_te[:, i], pred[:, i])
        # baseline: always predict the training mean
        base = np.full_like(y_te[:, i], y_tr[:, i].mean())
        base_r2 = r2_score(y_te[:, i], base)
        print(f"{ax:<10} {r2:>7.3f} {mae:>10.3f} {mae*scale:>9.3f} {base_r2:>11.3f}")

    true_q = _quadrant(y_te[:, 0], y_te[:, 1])
    pred_q = _quadrant(pred[:, 0], pred[:, 1])
    q_acc = float((true_q == pred_q).mean())
    print(f"\nQuadrant accuracy (4 mood regions): {q_acc:.3f}  (chance ~0.25)")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "axes": axes, "embed": "clap-htsat-unfused"}, out_path)
    print(f"Saved regression head -> {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--emb", type=Path, default=DEFAULT_EMB)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    main(args.emb, args.out)
