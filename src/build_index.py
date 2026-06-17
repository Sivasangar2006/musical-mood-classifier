"""
build_index.py
--------------
Loads the CNN embeddings saved by train_cnn.py and builds a FAISS index
for cosine similarity search.

For 999 vectors at 512-dim we use IndexFlatIP (exact, no approximation needed).
L2-normalised vectors -> inner product = cosine similarity.

Saves:
  models/faiss_index.bin  -- exact cosine index
  models/faiss_meta.json  -- {filenames, mood_labels, mood_names}
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import numpy as np
import faiss
from pathlib import Path

MODELS_DIR = Path("../models")


def build():
    print("Loading embeddings...")
    embeddings = np.load(MODELS_DIR / "cnn_embeddings.npy").astype("float32")
    labels     = np.load(MODELS_DIR / "cnn_labels.npy")
    with open(MODELS_DIR / "cnn_filenames.json") as f:
        filenames = json.load(f)

    MOOD_LABELS = ["Angry", "Energetic", "Happy", "Relaxed", "Sad"]
    mood_names  = [MOOD_LABELS[l] for l in labels]

    n, d = embeddings.shape
    print(f"  {n} embeddings, dim={d}")

    # L2-normalise so inner product == cosine similarity
    faiss.normalize_L2(embeddings)

    # Exact flat index — fast enough for <10k vectors
    index = faiss.IndexFlatIP(d)
    index.add(embeddings)

    faiss.write_index(index, str(MODELS_DIR / "faiss_index.bin"))
    print(f"  FAISS index written: {MODELS_DIR}/faiss_index.bin  ({index.ntotal} vectors)")

    meta = {
        "filenames":   filenames,
        "mood_labels": labels.tolist(),
        "mood_names":  mood_names,
    }
    with open(MODELS_DIR / "faiss_meta.json", "w") as f:
        json.dump(meta, f)
    print(f"  Meta written: {MODELS_DIR}/faiss_meta.json")
    print("Done.")


if __name__ == "__main__":
    build()
