"""
extract.py
----------
Runs on the GTZAN dataset folder, extracts audio features
from every .wav file, maps genre → mood, saves to data/features.csv
"""

import os
import librosa
import numpy as np
import pandas as pd
from tqdm import tqdm

# ─── Genre → Mood Mapping ───────────────────────────────────────────────────
MOOD_MAP = {
    "pop":       "Happy",
    "disco":     "Happy",
    "reggae":    "Happy",
    "hiphop":    "Energetic",
    "rock":      "Energetic",
    "metal":     "Angry",
    "blues":     "Sad",
    "country":   "Sad",
    "classical": "Relaxed",
    "jazz":      "Relaxed",
}

# ─── Feature Extraction ──────────────────────────────────────────────────────
def extract_features(file_path: str, duration: int = None) -> np.ndarray:
    """
    Load an audio clip and return a 1-D feature vector containing:
      - 13 MFCC means + 13 MFCC stds          = 26
      - 12 Chroma means                        = 12
      - Spectral centroid mean + std           =  2
      - Spectral rolloff mean + std            =  2
      - Spectral bandwidth mean + std          =  2
      - 7 Spectral contrast means              =  7
      - ZCR mean + std                         =  2
      - RMS mean + std                         =  2
      - Tempo (BPM)                            =  1
    Total                                      = 56 features
    """
    y, sr = librosa.load(file_path, duration=duration, mono=True)

    # MFCCs
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mfcc_mean = np.mean(mfcc, axis=1)   # shape (13,)
    mfcc_std  = np.std(mfcc,  axis=1)   # shape (13,)

    # Chroma
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)  # shape (12,)

    # Spectral features
    centroid  = librosa.feature.spectral_centroid(y=y, sr=sr)
    rolloff   = librosa.feature.spectral_rolloff(y=y, sr=sr)
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)
    contrast  = librosa.feature.spectral_contrast(y=y, sr=sr)

    # Time-domain features
    zcr = librosa.feature.zero_crossing_rate(y)
    rms = librosa.feature.rms(y=y)

    # Rhythm
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

    feature_vector = np.hstack([
        mfcc_mean, mfcc_std,                              # 26
        chroma_mean,                                      # 12
        np.mean(centroid),  np.std(centroid),             #  2
        np.mean(rolloff),   np.std(rolloff),              #  2
        np.mean(bandwidth), np.std(bandwidth),            #  2
        np.mean(contrast, axis=1),                        #  7
        np.mean(zcr),       np.std(zcr),                  #  2
        np.mean(rms),       np.std(rms),                  #  2
        float(tempo),                                     #  1
    ])
    return feature_vector


# ─── Column Names ────────────────────────────────────────────────────────────
def get_column_names() -> list:
    cols  = ["filename", "genre", "mood"]
    cols += [f"mfcc_mean_{i}" for i in range(13)]
    cols += [f"mfcc_std_{i}"  for i in range(13)]
    cols += [f"chroma_{i}"    for i in range(12)]
    cols += ["centroid_mean", "centroid_std"]
    cols += ["rolloff_mean",  "rolloff_std"]
    cols += ["bandwidth_mean","bandwidth_std"]
    cols += [f"contrast_{i}"  for i in range(7)]
    cols += ["zcr_mean", "zcr_std"]
    cols += ["rms_mean", "rms_std"]
    cols += ["tempo"]
    return cols


# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    # ── adjust this path to wherever GTZAN lives on your machine ──
    DATA_DIR   = os.path.join("..","data", "raw","Data", "genres_original")
    OUTPUT_CSV = os.path.join("..","data", "features.csv")

    if not os.path.exists(DATA_DIR):
        raise FileNotFoundError(
            f"\n[ERROR] Dataset folder not found: {DATA_DIR}\n"
            "Make sure the GTZAN dataset is at data/raw/genres_original/"
        )

    rows = []
    skipped = 0

    genre_folders = [g for g in os.listdir(DATA_DIR)
                     if os.path.isdir(os.path.join(DATA_DIR, g))]

    for genre in tqdm(genre_folders, desc="Genres"):
        mood = MOOD_MAP.get(genre, "Unknown")
        genre_path = os.path.join(DATA_DIR, genre)

        wav_files = [f for f in os.listdir(genre_path) if f.endswith(".wav")]

        for fname in tqdm(wav_files, desc=f"  {genre}", leave=False):
            fpath = os.path.join(genre_path, fname)
            try:
                feats = extract_features(fpath)
                rows.append([fname, genre, mood] + feats.tolist())
            except Exception as e:
                print(f"\n[SKIP] {fname}: {e}")
                skipped += 1

    df = pd.DataFrame(rows, columns=get_column_names())
    df.to_csv(OUTPUT_CSV, index=False)

    print(f"\n✅ Done!")
    print(f"   Tracks processed : {len(df)}")
    print(f"   Tracks skipped   : {skipped}")
    print(f"   Features per song: {len(df.columns) - 3}")
    print(f"   Saved to         : {OUTPUT_CSV}")
    print(f"\n   Mood distribution:\n{df['mood'].value_counts().to_string()}")


if __name__ == "__main__":
    main()
