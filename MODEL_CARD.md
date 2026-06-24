# Model Card — Dimensional Music Emotion Engine

## Overview
Predicts the **emotion of a song as a continuous point in valence–arousal space**
(Russell's circumplex), rather than a single mood label. Moods are regions of that
plane. Powers per-song analysis, similar-song and mood recommendations, and
cross-modal text-to-mood search.

## Architecture
- **Embeddings:** CLAP (`laion/clap-htsat-unfused`) — a pretrained audio–text model.
  Audio is decoded to 48 kHz mono, split into 10 s windows, embedded, and mean-pooled.
- **Head:** `RidgeCV` linear probe on the frozen 512-d embedding → (valence, arousal).
- **Out-of-distribution gate:** a CLAP zero-shot aggression detector corrects valence/
  arousal for music DEAM never contained (e.g. metal), which the linear head otherwise
  rates as falsely positive. The gate is off for in-distribution audio.
- **Recommendation:** cosine nearest-neighbour over a precomputed iTunes-preview corpus
  (in-memory; no vector DB needed at this scale).

## Training data
- **DEAM** (MediaEval Database for Emotional Analysis in Music): ~1,802 clips with
  continuous valence/arousal annotations on a 1–9 scale. 80/20 train/test split.
- **Continual learning:** user confirmations/corrections (stored with their embedding)
  are folded back via `backend/retrain_from_feedback.py`.

## Evaluation (held-out DEAM test split)
| Axis | R² | MAE (1–9) | Variance kept | Baseline R² |
|------|-----|-----------|---------------|-------------|
| Valence | **0.49** | 0.65 | 75% | ~0.00 |
| Arousal | **0.64** | 0.56 | 84% | ~0.00 |

- **Quadrant accuracy:** 0.67 (4 mood regions; chance = 0.25)
- Plots: `figures/va_scatter.png`, `va_calibration.png`, `va_quadrant_confusion.png`
- Regenerate: `PYTHONPATH=src python -m emotion.evaluate`

Valence is the harder axis in music-emotion research; a linear probe on frozen CLAP
beating R²≈0.5 is competitive with deep approaches. Baseline R²≈0 confirms genuine
learning rather than mean-prediction.

## Known limitations
- **Regression-to-the-mean:** predictions retain ~75–84% of the true variance, so
  extreme songs are pulled slightly toward neutral.
- **Out-of-distribution genres:** DEAM under-represents metal/extreme music. The
  zero-shot gate mitigates the worst failure (metal → "Happy") but is a patch, not a cure.
- **Label subjectivity:** musical emotion is inherently subjective; DEAM labels are
  averaged over annotators. "Consistency" in the UI is segment agreement, **not** a
  probability that the mood is correct.
- **Corpus:** recommendation corpus was seeded from mood-keyword searches and skews
  toward some genres; a curated rebuild would improve it.

## Intended use
Music discovery, demos, and education. Not for clinical, safety, or moderation use.
