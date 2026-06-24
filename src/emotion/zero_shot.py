"""Zero-shot correction for out-of-distribution music (the death-metal fix).

The DEAM-trained regression head is strong on the kind of music DEAM contains
(Western pop/rock/electronic) but extrapolates badly on music it never saw —
notably aggressive metal, which it confidently rates as high-valence "Happy".

CLAP itself, however, *does* separate aggressive music from happy music (provable
with zero-shot text cosine). So we use that: detect aggression via CLAP zero-shot,
and only where aggression is high do we blend the song's valence/arousal toward a
CLAP-derived prior. A "gate" keeps the correction OFF for normal music, so the
regressor's in-distribution accuracy (valence R² 0.51) is preserved — the gate
fires on ~11% of DEAM and costs ~0.02 R², while fixing the metal failure mode.

Calibration constants (how a zero-shot score maps onto the 1-9 valence scale) are
fit once on DEAM by `fit_calibration()` and saved to va_calib.json, which ships
with the backend. At serve time we recompute the text anchors from the saved
prompts (CLAP is already loaded) — no training data needed on the server.
"""

from __future__ import annotations

import functools
import json
from pathlib import Path

import numpy as np

from emotion.embed import embed_text

_REPO_ROOT = Path(__file__).resolve().parents[2]
CALIB_PATH = _REPO_ROOT / "artifacts" / "deam" / "va_calib.json"

# Text anchors. Valence axis = positive minus negative; arousal axis = high minus
# low; aggression = how "harsh/aggressive" the audio reads (the gate signal).
PROMPTS = {
    "pos": ["happy joyful cheerful uplifting music", "positive feel-good bright song"],
    "neg": ["angry aggressive harsh menacing music", "sad depressing gloomy song"],
    "hi":  ["intense energetic fast loud powerful music", "aggressive driving high-energy song"],
    "lo":  ["calm peaceful gentle quiet music", "slow soft relaxing tender song"],
    "agg": ["aggressive angry harsh screaming music", "heavy metal hardcore aggressive"],
}


@functools.lru_cache(maxsize=1)
def _anchors() -> dict:
    return {k: embed_text(v) for k, v in PROMPTS.items()}


def zero_shot_scores(embedding: np.ndarray) -> tuple[float, float, float]:
    """Return (valence_axis, arousal_axis, aggression) zero-shot scores for one embedding."""
    a = _anchors()
    e = np.asarray(embedding, dtype=np.float32)
    zsV = float((e @ a["pos"].T).mean() - (e @ a["neg"].T).mean())
    zsA = float((e @ a["hi"].T).mean() - (e @ a["lo"].T).mean())
    agg = float((e @ a["agg"].T).mean())
    return zsV, zsA, agg


@functools.lru_cache(maxsize=1)
def load_calib() -> dict | None:
    if not CALIB_PATH.is_file():
        return None
    return json.loads(CALIB_PATH.read_text(encoding="utf-8"))


def correct(embedding: np.ndarray, reg_valence: float, reg_arousal: float) -> dict:
    """Gate-corrected valence/arousal. Returns the corrected values + gate/agg for
    transparency. If no calibration is available, returns the regressor values."""
    calib = load_calib()
    if calib is None:
        return {"valence": reg_valence, "arousal": reg_arousal, "gate": 0.0, "aggression": 0.0}

    zsV, zsA, agg = zero_shot_scores(embedding)
    lo, hi = calib["agg_lo"], calib["agg_hi"]
    gate = float(np.clip((agg - lo) / max(hi - lo, 1e-6), 0.0, 1.0))

    cal_v = calib["a_v"] * zsV + calib["b_v"]
    cal_a = calib["a_a"] * zsA + calib["b_a"]
    valence = (1 - gate) * reg_valence + gate * cal_v
    arousal = (1 - gate) * reg_arousal + gate * cal_a
    return {
        "valence": float(np.clip(valence, -1, 1)),
        "arousal": float(np.clip(arousal, -1, 1)),
        "gate": round(gate, 3),
        "aggression": round(agg, 3),
    }


def fit_calibration(
    npz: Path | None = None,
    head_path: Path | None = None,
    out: Path = CALIB_PATH,
) -> dict:
    """Fit the zero-shot->scale calibration on DEAM and save it. Run once offline."""
    import joblib

    npz = npz or (_REPO_ROOT / "artifacts" / "deam" / "deam_clap.npz")
    head_path = head_path or (_REPO_ROOT / "artifacts" / "deam" / "va_head.joblib")

    d = np.load(npz)
    X = d["X"]
    yv, ya = d["valence"], d["arousal"]
    a = _anchors()
    zsV = (X @ a["pos"].T).mean(1) - (X @ a["neg"].T).mean(1)
    zsA = (X @ a["hi"].T).mean(1) - (X @ a["lo"].T).mean(1)
    agg = (X @ a["agg"].T).mean(1)

    # linear calibration zs-score -> DEAM scale, per axis
    def fit(zs, target):
        A = np.c_[zs, np.ones_like(zs)]
        slope, intercept = np.linalg.lstsq(A, target, rcond=None)[0]
        return float(slope), float(intercept)

    a_v, b_v = fit(zsV, yv)
    a_a, b_a = fit(zsA, ya)

    calib = {
        "agg_lo": float(np.percentile(agg, 90)),   # gate starts where DEAM gets intense
        "agg_hi": float(np.percentile(agg, 98)),    # full correction at the very aggressive end
        "a_v": a_v, "b_v": b_v, "a_a": a_a, "b_a": b_a,
        "prompts": PROMPTS,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(calib, indent=2), encoding="utf-8")
    load_calib.cache_clear()
    print(f"Saved calibration -> {out}")
    print(f"  gate range: agg {calib['agg_lo']:.3f}..{calib['agg_hi']:.3f}")
    return calib


if __name__ == "__main__":
    fit_calibration()
