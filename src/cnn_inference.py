"""
cnn_inference.py
----------------
Loads the fine-tuned ResNet18 and FAISS index.
Provides:
  predict_cnn(audio_path) → {mood, confidence, probabilities, embedding}
  find_similar(embedding, k) → [{filename, mood, score}]
"""

import json
import numpy as np
import torch
import torch.nn as nn
import librosa
import librosa.display
import matplotlib
matplotlib.use("Agg")   # headless — no display needed
import matplotlib.pyplot as plt
import faiss
from io import BytesIO
from PIL import Image
from pathlib import Path
from torchvision import models, transforms

MODELS_DIR  = Path(__file__).parent.parent / "models"
IMG_SIZE    = 224
MOOD_LABELS = ["Angry", "Energetic", "Happy", "Relaxed", "Sad"]
MOOD_META   = {
    "Happy":     {"emoji": "😊", "description": "Bright, upbeat, positive"},
    "Energetic": {"emoji": "⚡", "description": "Fast, driving, full of energy"},
    "Angry":     {"emoji": "😠", "description": "Intense, aggressive, heavy"},
    "Sad":       {"emoji": "😢", "description": "Melancholic, slow, introspective"},
    "Relaxed":   {"emoji": "😌", "description": "Calm, soothing, peaceful"},
}

_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225]),
])

# ─── Model + Index (loaded once on import) ───────────────────────────────────
_cnn_model    = None
_faiss_index  = None
_faiss_meta   = None


def _build_model():
    m = models.resnet18(weights=None)
    m.fc = nn.Linear(m.fc.in_features, len(MOOD_LABELS))
    return m


def load_cnn():
    global _cnn_model
    weights_path = MODELS_DIR / "cnn_model.pth"
    if not weights_path.exists():
        return False
    m = _build_model()
    state = torch.load(weights_path, map_location=_device, weights_only=True)
    m.load_state_dict(state)
    m.to(_device)
    m.eval()
    _cnn_model = m
    return True


def load_faiss():
    global _faiss_index, _faiss_meta
    index_path = MODELS_DIR / "faiss_index.bin"
    meta_path  = MODELS_DIR / "faiss_meta.json"
    if not index_path.exists() or not meta_path.exists():
        return False
    _faiss_index = faiss.read_index(str(index_path))
    with open(meta_path) as f:
        _faiss_meta = json.load(f)
    return True


# ─── Audio → Spectrogram tensor ──────────────────────────────────────────────
def _audio_to_tensor(audio_path: str, duration: int = 45) -> torch.Tensor:
    """Load audio, compute mel spectrogram, return (1, C, H, W) tensor."""
    y, sr = librosa.load(audio_path, duration=duration, mono=True)
    mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, fmax=8000)
    mel_db = librosa.power_to_db(mel, ref=np.max)

    # Render to RGB image in memory (same style as GTZAN pre-generated images)
    fig, ax = plt.subplots(figsize=(4, 3), dpi=72)
    librosa.display.specshow(mel_db, sr=sr, x_axis="time", y_axis="mel",
                             fmax=8000, ax=ax, cmap="viridis")
    ax.axis("off")
    fig.tight_layout(pad=0)

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0)
    plt.close(fig)

    buf.seek(0)
    img = Image.open(buf).convert("RGB")
    tensor = _transform(img).unsqueeze(0).to(_device)  # (1, 3, 224, 224)
    return tensor


# ─── Public API ──────────────────────────────────────────────────────────────
def predict_cnn(audio_path: str, duration: int = 45) -> dict:
    """
    Returns:
      mood, confidence, probabilities, embedding (list[float])
    """
    if _cnn_model is None:
        raise RuntimeError("CNN model not loaded — call load_cnn() first")

    tensor = _audio_to_tensor(audio_path, duration)

    # Capture 512-dim embedding via forward hook
    embedding_buf = {}
    def _hook(module, inp, out):
        embedding_buf["vec"] = inp[0].detach().cpu().numpy()[0]   # (512,)
    handle = _cnn_model.fc.register_forward_hook(_hook)

    with torch.no_grad():
        logits = _cnn_model(tensor)          # (1, 5)
        probs  = torch.softmax(logits, dim=1).cpu().numpy()[0]  # (5,)

    handle.remove()

    prob_dict = {MOOD_LABELS[i]: float(probs[i]) for i in range(len(MOOD_LABELS))}
    predicted_mood = max(prob_dict, key=prob_dict.get)
    confidence     = prob_dict[predicted_mood]

    return {
        "mood":          predicted_mood,
        "confidence":    confidence,
        "probabilities": prob_dict,
        "embedding":     embedding_buf["vec"].tolist(),
        **MOOD_META.get(predicted_mood, {"emoji": "🎵", "description": ""}),
    }


def find_similar(embedding: list, k: int = 5) -> list[dict]:
    """
    Cosine similarity search via FAISS.
    Returns list of {filename, mood, score} dicts.
    """
    if _faiss_index is None or _faiss_meta is None:
        return []

    vec = np.array(embedding, dtype="float32").reshape(1, -1)
    faiss.normalize_L2(vec)

    scores, indices = _faiss_index.search(vec, k + 1)  # +1 to skip self
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        results.append({
            "filename": _faiss_meta["filenames"][idx],
            "mood":     _faiss_meta["mood_names"][idx],
            "score":    round(float(score), 4),
        })
    # drop the top-1 if it's a perfect match (the query itself)
    if results and results[0]["score"] > 0.999:
        results = results[1:]
    return results[:k]
