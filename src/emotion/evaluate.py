"""Evaluation dashboard for the valence/arousal engine.

Computes honest, portfolio-grade metrics on the DEAM held-out split and writes:
  - artifacts/eval/metrics.json   (served by GET /va/metrics)
  - figures/va_scatter.png, va_calibration.png, va_quadrant_confusion.png

Metrics reported, per axis (valence is the hard one in MIR):
  - R2, MAE (normalised and on the interpretable 1-9 scale)
  - a mean-predictor baseline R2 (so the numbers are contextualised)
  - variance ratio (pred std / true std) — quantifies regression-to-the-mean
  - calibration reliability (binned predicted vs actual)
And overall:
  - quadrant confusion matrix + accuracy (continuous V/A -> 4 mood regions)
  - effect of the zero-shot gate on in-distribution DEAM (should be ~negligible)

Run: PYTHONPATH=src python -m emotion.evaluate
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import joblib
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.model_selection import train_test_split

from emotion.deam import VA_SCALE_MAX, VA_SCALE_MID
from emotion.zero_shot import correct as zs_correct

_ROOT = Path(__file__).resolve().parents[2]
EMB = _ROOT / "artifacts" / "deam" / "deam_clap.npz"
HEAD = _ROOT / "artifacts" / "deam" / "va_head.joblib"
EVAL_DIR = _ROOT / "artifacts" / "eval"
FIG_DIR = _ROOT / "figures"
QUAD_NAMES = ["happy/excited", "tense/angry", "calm/content", "sad/depressed"]


def _quadrant(v: np.ndarray, a: np.ndarray) -> np.ndarray:
    """0=+V+A 1=-V+A 2=+V-A 3=-V-A."""
    return np.where(v >= 0, np.where(a >= 0, 0, 2), np.where(a >= 0, 1, 3))


def _apply_gate(X: np.ndarray, reg: np.ndarray) -> np.ndarray:
    """Apply the serving-time zero-shot correction to each row (no audio needed)."""
    out = reg.copy()
    for i in range(len(X)):
        c = zs_correct(X[i], float(reg[i, 0]), float(reg[i, 1]))
        out[i] = [c["valence"], c["arousal"]]
    return out


def evaluate() -> dict:
    d = np.load(EMB)
    X = d["X"]
    y = np.stack([d["valence"], d["arousal"]], axis=1)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)

    head = joblib.load(HEAD)["model"]
    reg = head.predict(Xte)
    corrected = _apply_gate(Xte, reg)
    scale = VA_SCALE_MAX - VA_SCALE_MID

    axes = {}
    for i, name in enumerate(["valence", "arousal"]):
        base = np.full(len(yte), ytr[:, i].mean())
        # calibration: 10 bins over predicted range, mean predicted vs mean actual
        pred = corrected[:, i]
        bins = np.linspace(pred.min(), pred.max(), 11)
        idx = np.clip(np.digitize(pred, bins) - 1, 0, 9)
        calib = []
        for b in range(10):
            m = idx == b
            if m.any():
                calib.append({"pred": round(float(pred[m].mean()), 3),
                              "actual": round(float(yte[m, i].mean()), 3),
                              "n": int(m.sum())})
        axes[name] = {
            "r2": round(float(r2_score(yte[:, i], corrected[:, i])), 3),
            "r2_raw_head": round(float(r2_score(yte[:, i], reg[:, i])), 3),
            "mae_norm": round(float(mean_absolute_error(yte[:, i], corrected[:, i])), 3),
            "mae_1to9": round(float(mean_absolute_error(yte[:, i], corrected[:, i]) * scale), 3),
            "baseline_r2": round(float(r2_score(yte[:, i], base)), 3),
            "variance_ratio": round(float(corrected[:, i].std() / yte[:, i].std()), 3),
            "calibration": calib,
        }

    # quadrant confusion
    tq = _quadrant(yte[:, 0], yte[:, 1])
    pq = _quadrant(corrected[:, 0], corrected[:, 1])
    conf = np.zeros((4, 4), int)
    for t, p in zip(tq, pq):
        conf[t, p] += 1
    quad_acc = float((tq == pq).mean())

    metrics = {
        "dataset": "DEAM", "n_train": int(len(Xtr)), "n_test": int(len(Xte)),
        "embedding": "CLAP (laion/clap-htsat-unfused)", "head": "RidgeCV + zero-shot gate",
        "axes": axes,
        "quadrant_accuracy": round(quad_acc, 3),
        "quadrant_labels": QUAD_NAMES,
        "quadrant_confusion": conf.tolist(),
    }
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    (EVAL_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Saved metrics -> {EVAL_DIR / 'metrics.json'}")
    _plots(yte, corrected, conf)
    return metrics


def _plots(yte: np.ndarray, pred: np.ndarray, conf: np.ndarray) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[INFO] matplotlib not installed — skipping plots.")
        return
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    # 1) predicted vs true scatter, both axes
    fig, ax = plt.subplots(1, 2, figsize=(10, 4.5))
    for i, name in enumerate(["Valence", "Arousal"]):
        ax[i].scatter(yte[:, i], pred[:, i], s=8, alpha=0.3, color="#7c3aed")
        ax[i].plot([-1, 1], [-1, 1], "--", color="#888", lw=1)
        ax[i].set_xlabel(f"true {name}"); ax[i].set_ylabel(f"predicted {name}")
        ax[i].set_title(name); ax[i].set_xlim(-1, 1); ax[i].set_ylim(-1, 1)
    fig.tight_layout(); fig.savefig(FIG_DIR / "va_scatter.png", dpi=110); plt.close(fig)

    # 2) calibration reliability
    fig, ax = plt.subplots(1, 2, figsize=(10, 4.5))
    for i, name in enumerate(["Valence", "Arousal"]):
        order = np.argsort(pred[:, i])
        binned = np.array_split(order, 10)
        px = [pred[b, i].mean() for b in binned]
        py = [yte[b, i].mean() for b in binned]
        ax[i].plot([-1, 1], [-1, 1], "--", color="#888", lw=1, label="ideal")
        ax[i].plot(px, py, "o-", color="#10b981")
        ax[i].set_xlabel(f"predicted {name}"); ax[i].set_ylabel(f"actual {name}")
        ax[i].set_title(f"{name} calibration"); ax[i].legend()
    fig.tight_layout(); fig.savefig(FIG_DIR / "va_calibration.png", dpi=110); plt.close(fig)

    # 3) quadrant confusion heatmap
    fig, ax = plt.subplots(figsize=(5.5, 5))
    ax.imshow(conf, cmap="Purples")
    ax.set_xticks(range(4)); ax.set_yticks(range(4))
    ax.set_xticklabels(QUAD_NAMES, rotation=30, ha="right", fontsize=8)
    ax.set_yticklabels(QUAD_NAMES, fontsize=8)
    ax.set_xlabel("predicted"); ax.set_ylabel("true"); ax.set_title("Quadrant confusion")
    for r in range(4):
        for c in range(4):
            ax.text(c, r, conf[r, c], ha="center", va="center",
                    color="white" if conf[r, c] > conf.max() / 2 else "black")
    fig.tight_layout(); fig.savefig(FIG_DIR / "va_quadrant_confusion.png", dpi=110); plt.close(fig)
    print(f"Saved 3 plots -> {FIG_DIR}")


if __name__ == "__main__":
    m = evaluate()
    print("\n=== Summary ===")
    for ax, v in m["axes"].items():
        print(f"{ax:8} R2={v['r2']:.3f}  MAE(1-9)={v['mae_1to9']:.3f}  "
              f"var_ratio={v['variance_ratio']:.2f}  baseline_R2={v['baseline_r2']:.3f}")
    print(f"quadrant accuracy: {m['quadrant_accuracy']:.3f}")
