import librosa
import numpy as np
import pandas as pd
import os
from tqdm import tqdm

MOOD_MAP = {
    'pop':'Happy','disco':'Happy','hiphop':'Energetic',
    'rock':'Energetic','metal':'Angry','blues':'Sad',
    'classical':'Relaxed','jazz':'Relaxed',
    'reggae':'Happy','country':'Sad'
}

def extract_features(path):
    y, sr = librosa.load(path, duration=30, mono=True)

    mfcc     = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    chroma   = librosa.feature.chroma_stft(y=y, sr=sr)
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
    contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
    zcr      = librosa.feature.zero_crossing_rate(y)
    rms      = librosa.feature.rms(y=y)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

    return np.hstack([
        np.mean(mfcc, axis=1), np.std(mfcc, axis=1),
        np.mean(chroma, axis=1),
        np.mean(centroid), np.std(centroid),
        np.mean(contrast, axis=1),
        np.mean(zcr), np.std(zcr),
        np.mean(rms), np.std(rms),
        float(tempo)
    ])

rows = []
data_dir = "data/raw/Data/genres_original"

for genre in tqdm(os.listdir(data_dir)):
    genre_path = os.path.join(data_dir, genre)
    if not os.path.isdir(genre_path): continue
    mood = MOOD_MAP.get(genre, 'Unknown')

    for fname in os.listdir(genre_path):
        if not fname.endswith('.wav'): continue
        fpath = os.path.join(genre_path, fname)
        try:
            feats = extract_features(fpath)
            rows.append([fname, genre, mood] + feats.tolist())
        except Exception as e:
            print(f"Skipped {fname}: {e}")

cols = (['filename','genre','mood']
      + [f'mfcc_mean_{i}' for i in range(13)]
      + [f'mfcc_std_{i}' for i in range(13)]
      + [f'chroma_{i}' for i in range(12)]
      + ['centroid_mean','centroid_std']
      + [f'contrast_{i}' for i in range(7)]
      + ['zcr_mean','zcr_std','rms_mean','rms_std','tempo'])

df = pd.DataFrame(rows, columns=cols)
df.to_csv("data/features.csv", index=False)
print(f"Done. {len(df)} tracks → data/features.csv")