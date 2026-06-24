"""DEAM dataset loader for dimensional music-emotion modelling.

DEAM (MediaEval Database for Emotional Analysis in Music) provides ~1,802 music
clips, each annotated with a continuous *valence* and *arousal* value on a 1-9
scale (5 = neutral). This is the training data for our regression head: instead
of predicting one discrete mood, we predict a point in the 2-D emotion plane and
let moods be regions of that plane.

Layout (as shipped by the Kaggle `imsparsh/deam-mediaeval-dataset` mirror):

    <root>/
      DEAM_audio/MEMD_audio/<song_id>.mp3
      DEAM_Annotations/annotations/annotations averaged per song/song_level/
        static_annotations_averaged_songs_1_2000.csv
        static_annotations_averaged_songs_2000_2058.csv

The static CSVs have columns (note the leading spaces in the raw header):
    song_id, valence_mean, valence_std, arousal_mean, arousal_std
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

# Default to the local Kaggle cache, overridable via the DEAM_ROOT env var so the
# same code runs on a teammate's machine or in CI without edits.
_DEFAULT_ROOT = (
    r"C:\Users\LENOVO\.cache\kagglehub\datasets\imsparsh"
    r"\deam-mediaeval-dataset-emotional-analysis-in-music\versions\1"
)

# DEAM annotations live on a 1-9 Likert scale; 5 is emotional neutral.
VA_SCALE_MIN = 1.0
VA_SCALE_MAX = 9.0
VA_SCALE_MID = 5.0


def deam_root() -> Path:
    """Resolve the DEAM dataset root (env var DEAM_ROOT wins over the default)."""
    return Path(os.environ.get("DEAM_ROOT", _DEFAULT_ROOT))


def _static_annotation_dir(root: Path) -> Path:
    return (
        root
        / "DEAM_Annotations"
        / "annotations"
        / "annotations averaged per song"
        / "song_level"
    )


def _audio_dir(root: Path) -> Path:
    return root / "DEAM_audio" / "MEMD_audio"


def to_unit(value: pd.Series | float) -> pd.Series | float:
    """Map a raw 1-9 annotation to [-1, 1] (so 5 -> 0, the neutral centre)."""
    return (value - VA_SCALE_MID) / (VA_SCALE_MAX - VA_SCALE_MID)


def from_unit(value: float) -> float:
    """Inverse of :func:`to_unit` — map [-1, 1] back to the 1-9 DEAM scale."""
    return value * (VA_SCALE_MAX - VA_SCALE_MID) + VA_SCALE_MID


@dataclass(frozen=True)
class DeamStats:
    n_annotations: int
    n_with_audio: int
    n_missing_audio: int
    valence_range: tuple[float, float]
    arousal_range: tuple[float, float]


def load_deam_manifest(root: Path | None = None, require_audio: bool = True) -> pd.DataFrame:
    """Load DEAM into a tidy manifest joining annotations to audio file paths.

    Returns a DataFrame with columns:
        song_id, audio_path,
        valence_mean, arousal_mean, valence_std, arousal_std,   (raw 1-9)
        valence, arousal                                        (normalised [-1,1])

    Args:
        root: dataset root; defaults to :func:`deam_root`.
        require_audio: if True, drop rows whose .mp3 is missing on disk.
    """
    root = root or deam_root()
    ann_dir = _static_annotation_dir(root)
    audio_dir = _audio_dir(root)

    csvs = sorted(ann_dir.glob("static_annotations_averaged_songs_*.csv"))
    if not csvs:
        raise FileNotFoundError(f"No DEAM static annotation CSVs found in {ann_dir}")

    frames = []
    for csv in csvs:
        # skipinitialspace strips the leading space in " valence_mean" etc.
        df = pd.read_csv(csv, skipinitialspace=True)
        df.columns = [c.strip() for c in df.columns]
        frames.append(df)
    ann = pd.concat(frames, ignore_index=True).drop_duplicates(subset="song_id")

    keep = ["song_id", "valence_mean", "valence_std", "arousal_mean", "arousal_std"]
    ann = ann[keep].copy()
    ann["song_id"] = ann["song_id"].astype(int)

    ann["audio_path"] = ann["song_id"].map(lambda s: str(audio_dir / f"{s}.mp3"))
    ann["has_audio"] = ann["audio_path"].map(lambda p: Path(p).is_file())

    if require_audio:
        ann = ann[ann["has_audio"]].copy()

    # Normalised targets the model actually regresses on.
    ann["valence"] = to_unit(ann["valence_mean"])
    ann["arousal"] = to_unit(ann["arousal_mean"])

    cols = [
        "song_id", "audio_path",
        "valence_mean", "arousal_mean", "valence_std", "arousal_std",
        "valence", "arousal", "has_audio",
    ]
    return ann[cols].reset_index(drop=True)


def describe(root: Path | None = None) -> DeamStats:
    """Quick integrity check: how many annotations, how many have audio, ranges."""
    full = load_deam_manifest(root, require_audio=False)
    with_audio = int(full["has_audio"].sum())
    return DeamStats(
        n_annotations=len(full),
        n_with_audio=with_audio,
        n_missing_audio=len(full) - with_audio,
        valence_range=(float(full["valence_mean"].min()), float(full["valence_mean"].max())),
        arousal_range=(float(full["arousal_mean"].min()), float(full["arousal_mean"].max())),
    )


if __name__ == "__main__":
    stats = describe()
    print("DEAM dataset integrity check")
    print(f"  annotations:        {stats.n_annotations}")
    print(f"  with audio on disk: {stats.n_with_audio}")
    print(f"  missing audio:      {stats.n_missing_audio}")
    print(f"  valence range 1-9:  {stats.valence_range}")
    print(f"  arousal range 1-9:  {stats.arousal_range}")
    mani = load_deam_manifest()
    print("\nFirst 3 rows of the training manifest:")
    print(mani.head(3).to_string(index=False))
