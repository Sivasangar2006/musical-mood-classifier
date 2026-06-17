"""
extract_embeddings.py
---------------------
Loads the trained CNN and extracts embeddings for all GTZAN spectrogram images.
Run this once after train_cnn.py completes.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path
from PIL import Image
from torchvision import models, transforms
from torch.utils.data import Dataset, DataLoader

IMAGES_DIR  = Path("../data/raw/Data/images_original")
MODELS_DIR  = Path("../models")
IMG_SIZE    = 224
MOOD_LABELS = ["Angry", "Energetic", "Happy", "Relaxed", "Sad"]
MOOD_MAP = {
    "pop": "Happy", "disco": "Happy", "reggae": "Happy",
    "hiphop": "Energetic", "rock": "Energetic",
    "metal": "Angry",
    "blues": "Sad", "country": "Sad",
    "classical": "Relaxed", "jazz": "Relaxed",
}
MOOD_TO_IDX = {m: i for i, m in enumerate(MOOD_LABELS)}
device = torch.device("cpu")

transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


class SpectrogramDataset(Dataset):
    def __init__(self, paths, labels):
        self.paths = paths
        self.labels = labels
    def __len__(self): return len(self.paths)
    def __getitem__(self, i):
        img = Image.open(self.paths[i]).convert("RGB")
        return transform(img), self.labels[i]


def build_model():
    m = models.resnet18(weights=None)
    m.fc = nn.Linear(m.fc.in_features, len(MOOD_LABELS))
    return m


def main():
    print("Loading dataset paths...")
    paths, labels, filenames = [], [], []
    for genre_dir in sorted(IMAGES_DIR.iterdir()):
        if not genre_dir.is_dir(): continue
        mood = MOOD_MAP.get(genre_dir.name)
        if mood is None: continue
        for img in sorted(genre_dir.glob("*.png")):
            paths.append(str(img))
            labels.append(MOOD_TO_IDX[mood])
            filenames.append(img.name)
    print(f"  {len(paths)} images found")

    print("Loading CNN model...")
    model = build_model()
    state = torch.load(MODELS_DIR / "cnn_model.pth", map_location=device, weights_only=True)
    model.load_state_dict(state)
    model.to(device).eval()

    ds = SpectrogramDataset(paths, labels)
    loader = DataLoader(ds, batch_size=32, shuffle=False, num_workers=0)

    embeddings, all_labels = [], []
    features = {}

    def hook(module, inp, out):
        features["vec"] = inp[0].detach().cpu().numpy()

    handle = model.fc.register_forward_hook(hook)

    print("Extracting embeddings...")
    with torch.no_grad():
        for i, (imgs, lbls) in enumerate(loader):
            model(imgs.to(device))
            embeddings.append(features["vec"])
            all_labels.extend(lbls.numpy())
            if (i + 1) % 5 == 0:
                print(f"  batch {i+1}/{len(loader)}")

    handle.remove()

    emb_arr = np.vstack(embeddings)
    lbl_arr = np.array(all_labels)

    np.save(MODELS_DIR / "cnn_embeddings.npy", emb_arr)
    np.save(MODELS_DIR / "cnn_labels.npy",     lbl_arr)
    with open(MODELS_DIR / "cnn_filenames.json", "w") as f:
        json.dump(filenames, f)

    print(f"Done. Saved {len(emb_arr)} embeddings, shape={emb_arr.shape}")


if __name__ == "__main__":
    main()
