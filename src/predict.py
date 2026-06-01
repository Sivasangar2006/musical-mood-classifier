"""
predict.py
----------
Load a saved model and predict the mood of any audio file.

Usage:
    python src/predict.py path/to/song.wav
"""

import sys
import os
import joblib
import numpy as np

# reuse the feature extractor from extract.py
sys.path.append(os.path.dirname(__file__))
from extract import extract_features

MODELS_DIR = os.path.join("..", "models")


def load_model():
    model   = joblib.load(os.path.join(MODELS_DIR, "model.pkl"))
    scaler  = joblib.load(os.path.join(MODELS_DIR, "scaler.pkl"))
    encoder = joblib.load(os.path.join(MODELS_DIR, "encoder.pkl"))
    return model, scaler, encoder


def predict(file_path: str) -> dict:
    model, scaler, encoder = load_model()

    print(f"Extracting features from: {file_path}")
    feats = extract_features(file_path).reshape(1, -1)
    feats_scaled = scaler.transform(feats)

    proba     = model.predict_proba(feats_scaled)[0]
    pred_idx  = np.argmax(proba)
    pred_mood = encoder.classes_[pred_idx]
    confidence = proba[pred_idx]

    result = {
        "file":       file_path,
        "mood":       pred_mood,
        "confidence": confidence,
        "all_probs":  dict(zip(encoder.classes_, proba)),
    }
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/predict.py <path_to_audio.wav>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"[ERROR] File not found: {file_path}")
        sys.exit(1)

    result = predict(file_path)

    print(f"\n{'='*40}")
    print(f"  FILE       : {os.path.basename(result['file'])}")
    print(f"  MOOD       : {result['mood'].upper()}")
    print(f"  CONFIDENCE : {result['confidence']:.1%}")
    print(f"{'='*40}")
    print("  All probabilities:")
    for mood, prob in sorted(result["all_probs"].items(),
                              key=lambda x: -x[1]):
        bar = "█" * int(prob * 30)
        print(f"    {mood:<10} {prob:.1%}  {bar}")
    print(f"{'='*40}\n")


if __name__ == "__main__":
    main()
