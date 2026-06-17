"""
train_cnn.py
------------
Fine-tunes ResNet18 on GTZAN mel spectrogram images.
Saves:
  models/cnn_model.pth   — full model weights
  models/cnn_embeddings.npy  — 512-dim embedding for every training image
  models/cnn_labels.npy      — corresponding mood labels
  models/cnn_filenames.json  — corresponding filenames
"""

import os
import json
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from PIL import Image
from pathlib import Path

# ─── Config ──────────────────────────────────────────────────────────────────
IMAGES_DIR  = Path("../data/raw/Data/images_original")
MODELS_DIR  = Path("../models")
RANDOM_SEED = 42
EPOCHS      = 20
BATCH_SIZE  = 32
LR          = 1e-4
IMG_SIZE    = 224

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

MOOD_LABELS = ["Angry", "Energetic", "Happy", "Relaxed", "Sad"]
MOOD_TO_IDX = {m: i for i, m in enumerate(MOOD_LABELS)}

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

# ─── Dataset ─────────────────────────────────────────────────────────────────
class SpectrogramDataset(Dataset):
    def __init__(self, image_paths, labels, transform=None):
        self.image_paths = image_paths
        self.labels      = labels
        self.transform   = transform

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        img = Image.open(self.image_paths[idx]).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, self.labels[idx]


def load_dataset():
    paths, labels, filenames = [], [], []
    for genre_dir in sorted(IMAGES_DIR.iterdir()):
        if not genre_dir.is_dir():
            continue
        mood = MOOD_MAP.get(genre_dir.name)
        if mood is None:
            continue
        for img_path in sorted(genre_dir.glob("*.png")):
            paths.append(str(img_path))
            labels.append(MOOD_TO_IDX[mood])
            filenames.append(img_path.name)
    return paths, labels, filenames


# ─── Model ───────────────────────────────────────────────────────────────────
def build_model(num_classes=5):
    model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
    # Freeze early layers — only fine-tune the last block + classifier
    for name, param in model.named_parameters():
        if "layer4" not in name and "fc" not in name:
            param.requires_grad = False
    # Replace final FC layer for 5-class mood output
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model.to(device)


# ─── Embedding extractor (penultimate layer = 512-dim) ────────────────────────
def extract_embeddings(model, loader):
    model.eval()
    embeddings, all_labels = [], []

    # Hook to capture the 512-dim vector before the final FC layer
    features = {}
    def hook(module, input, output):
        features["embedding"] = input[0].detach().cpu().numpy()

    handle = model.fc.register_forward_hook(hook)

    with torch.no_grad():
        for imgs, labels in loader:
            imgs = imgs.to(device)
            model(imgs)
            embeddings.append(features["embedding"])
            all_labels.extend(labels.numpy())

    handle.remove()
    return np.vstack(embeddings), np.array(all_labels)


# ─── Training ────────────────────────────────────────────────────────────────
def train():
    print("=" * 55)
    print("  CNN MOOD CLASSIFIER — TRAINING")
    print("=" * 55)

    paths, labels, filenames = load_dataset()
    print(f"Total images: {len(paths)}")

    # Stratified train/test split
    train_paths, test_paths, train_labels, test_labels, train_files, test_files = \
        train_test_split(paths, labels, filenames, test_size=0.2,
                         stratify=labels, random_state=RANDOM_SEED)

    # ImageNet-style normalization + augmentation for training
    train_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406],
                             [0.229, 0.224, 0.225]),
    ])
    test_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406],
                             [0.229, 0.224, 0.225]),
    ])

    train_ds = SpectrogramDataset(train_paths, train_labels, train_tf)
    test_ds  = SpectrogramDataset(test_paths,  test_labels,  test_tf)
    full_ds  = SpectrogramDataset(paths, labels, test_tf)  # for embeddings

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,  num_workers=0)
    test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    full_loader  = DataLoader(full_ds,  batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    # Class weights for imbalance (Angry = 100, Happy = 300)
    counts = np.bincount(train_labels)
    weights = torch.tensor(1.0 / counts, dtype=torch.float32).to(device)

    model     = build_model()
    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()), lr=LR
    )
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=7, gamma=0.1)

    best_acc  = 0.0
    best_state = None

    for epoch in range(1, EPOCHS + 1):
        # ── Train ──
        model.train()
        running_loss, correct, total = 0.0, 0, 0
        for imgs, lbls in train_loader:
            imgs, lbls = imgs.to(device), lbls.to(device)
            optimizer.zero_grad()
            out  = model(imgs)
            loss = criterion(out, lbls)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * imgs.size(0)
            correct      += (out.argmax(1) == lbls).sum().item()
            total        += imgs.size(0)
        scheduler.step()

        train_acc = correct / total

        # ── Validate ──
        model.eval()
        val_correct, val_total = 0, 0
        with torch.no_grad():
            for imgs, lbls in test_loader:
                imgs, lbls = imgs.to(device), lbls.to(device)
                out = model(imgs)
                val_correct += (out.argmax(1) == lbls).sum().item()
                val_total   += imgs.size(0)
        val_acc = val_correct / val_total

        print(f"Epoch {epoch:2d}/{EPOCHS}  "
              f"loss={running_loss/total:.4f}  "
              f"train_acc={train_acc:.3f}  val_acc={val_acc:.3f}")

        if val_acc > best_acc:
            best_acc   = val_acc
            best_state = {k: v.clone() for k, v in model.state_dict().items()}

    # ── Final evaluation ──
    model.load_state_dict(best_state)
    model.eval()
    all_preds, all_true = [], []
    with torch.no_grad():
        for imgs, lbls in test_loader:
            imgs = imgs.to(device)
            preds = model(imgs).argmax(1).cpu().numpy()
            all_preds.extend(preds)
            all_true.extend(lbls.numpy())

    print(f"\nBest val accuracy: {best_acc:.3f}")
    print(classification_report(all_true, all_preds, target_names=MOOD_LABELS))

    # ── Save model ──
    MODELS_DIR.mkdir(exist_ok=True)
    torch.save(best_state, MODELS_DIR / "cnn_model.pth")
    print(f"Saved model -> {MODELS_DIR / 'cnn_model.pth'}")

    # ── Extract and save all embeddings ──
    print("\nExtracting embeddings for all 999 songs...")
    embeddings, emb_labels = extract_embeddings(model, full_loader)
    np.save(MODELS_DIR / "cnn_embeddings.npy", embeddings)
    np.save(MODELS_DIR / "cnn_labels.npy",     emb_labels)
    with open(MODELS_DIR / "cnn_filenames.json", "w") as f:
        json.dump(filenames, f)

    print(f"Saved {len(embeddings)} embeddings -> {MODELS_DIR}/cnn_embeddings.npy")
    print(f"Embedding shape: {embeddings.shape}")


if __name__ == "__main__":
    train()
