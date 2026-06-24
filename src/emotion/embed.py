"""CLAP audio/text embeddings — the shared representation for the whole engine.

We use LAION-CLAP (`laion/clap-htsat-unfused`) via Hugging Face. CLAP maps audio
*and* natural-language text into the SAME 512-d space, which buys us three things
from one model:

  1. audio -> embedding  : input to the valence/arousal regression head (Phase 1)
  2. embedding similarity : recommendation by nearest-neighbour search (Phase 1)
  3. text  -> embedding  : zero-shot mood labels + "rainy sunday drive" search (Phase 2)

CLAP expects 48 kHz mono audio. DEAM clips are ~45 s, longer than CLAP's ~10 s
window, so we deterministically split each clip into 10 s chunks, embed each, and
mean-pool. Deterministic (no random crop) means embeddings are cacheable and
reproducible — which matters once we precompute thousands of them offline.
"""

from __future__ import annotations

import functools
import hashlib
import os
from pathlib import Path

import librosa
import numpy as np
import torch

CLAP_MODEL_ID = "laion/clap-htsat-unfused"
SAMPLE_RATE = 48_000
CHUNK_SECONDS = 10
EMBED_DIM = 512


@functools.lru_cache(maxsize=1)
def _load_model():
    """Load CLAP once and cache it. Returns (model, processor) on CPU, eval mode."""
    from transformers import ClapModel, ClapProcessor

    model = ClapModel.from_pretrained(CLAP_MODEL_ID)
    processor = ClapProcessor.from_pretrained(CLAP_MODEL_ID)
    model.eval()
    return model, processor


def _l2_normalize(x: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(x, axis=-1, keepdims=True)
    return x / np.clip(norm, 1e-8, None)


def _load_audio_av(path: str) -> np.ndarray:
    """Decode any container (m4a/aac/mp3/...) to 48 kHz mono float32 via PyAV.

    PyAV bundles ffmpeg in its wheel, so this works with no system ffmpeg — which
    is what we need for iTunes previews (.m4a) both locally and on free-tier hosts.
    """
    import av  # imported lazily so the dependency is only needed for exotic formats

    container = av.open(path)
    resampler = av.audio.resampler.AudioResampler(format="flt", layout="mono", rate=SAMPLE_RATE)
    parts: list[np.ndarray] = []
    for frame in container.decode(audio=0):
        for rframe in resampler.resample(frame):          # newer PyAV returns a list
            parts.append(rframe.to_ndarray().reshape(-1))
    container.close()
    if not parts:
        return np.zeros(SAMPLE_RATE, dtype=np.float32)
    return np.concatenate(parts).astype(np.float32)


def _load_audio(path: str | Path) -> np.ndarray:
    """Load an audio file as 48 kHz mono float32.

    Tries librosa (libsndfile — fast for wav/mp3); falls back to PyAV for formats
    libsndfile can't handle (notably m4a/aac iTunes previews).
    """
    try:
        wav, _ = librosa.load(str(path), sr=SAMPLE_RATE, mono=True)
        return wav.astype(np.float32)
    except Exception:
        return _load_audio_av(str(path))


def _chunk(wav: np.ndarray, chunk_s: int = CHUNK_SECONDS) -> list[np.ndarray]:
    """Split a waveform into non-overlapping chunks of `chunk_s` seconds.

    A final short remainder (> 1 s) is kept; clips shorter than one chunk return
    a single chunk. Empty/near-silent inputs return one zero chunk so callers
    always get at least one embedding.
    """
    size = chunk_s * SAMPLE_RATE
    if wav.size < SAMPLE_RATE:  # < 1 s of audio
        return [np.zeros(size, dtype=np.float32)]
    chunks = [wav[i:i + size] for i in range(0, wav.size, size)]
    # Drop a trailing sliver shorter than 1 s — too little signal to be useful.
    if len(chunks) > 1 and chunks[-1].size < SAMPLE_RATE:
        chunks = chunks[:-1]
    return chunks


@torch.no_grad()
def embed_audio_full(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Return (pooled, per_chunk) CLAP embeddings for an audio file.

    - pooled    : (512,)  mean of the raw chunk features, then L2-normalised.
                  This is the EXACT vector training used — keep it that way so the
                  regression head sees the same distribution at serve time.
    - per_chunk : (n, 512) each chunk's embedding, L2-normalised. Used at serve
                  time to predict per-chunk and measure temporal agreement, which
                  gives an honest confidence signal the linear head can't provide.
    """
    model, processor = _load_model()
    chunks = _chunk(_load_audio(path))
    inputs = processor(audio=chunks, sampling_rate=SAMPLE_RATE, return_tensors="pt")
    feats = model.get_audio_features(**inputs).cpu().numpy()   # (n_chunks, 512) raw
    pooled = _l2_normalize(feats.mean(axis=0))
    per_chunk = _l2_normalize(feats)
    return pooled, per_chunk


def embed_audio_file(path: str | Path) -> np.ndarray:
    """Return one L2-normalised 512-d CLAP embedding (mean-pooled over chunks)."""
    pooled, _ = embed_audio_full(path)
    return pooled


# ─── Content-hash embedding cache (production: skip recompute on repeat audio) ───
# CLAP inference is the expensive part of a request (~3s CPU). The same preview /
# upload analysed twice should be instant. We key the cache on the SHA-256 of the
# file bytes, so it's path-independent and self-invalidating if the audio changes.
_CACHE_DIR = Path(os.getenv("EMB_CACHE", Path(__file__).resolve().parents[2] / "artifacts" / "cache" / "emb"))


def _file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def embed_audio_full_cached(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """embed_audio_full with a disk cache keyed by file content hash."""
    try:
        key = _file_sha256(path)
        cache_f = _CACHE_DIR / f"{key}.npz"
        if cache_f.is_file():
            d = np.load(cache_f)
            return d["pooled"], d["chunks"]
    except Exception:  # noqa: BLE001 — cache problems must never break inference
        cache_f = None

    pooled, per_chunk = embed_audio_full(path)
    if cache_f is not None:
        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            np.savez(cache_f, pooled=pooled, chunks=per_chunk)
        except Exception:  # noqa: BLE001
            pass
    return pooled, per_chunk


@torch.no_grad()
def embed_audio_files(paths: list[str | Path], log_every: int = 50) -> np.ndarray:
    """Embed many audio files. Returns (N, 512) L2-normalised embeddings.

    Files are processed one at a time (each is internally chunk-batched), which
    keeps peak memory flat — important for free-tier CPU boxes.
    """
    out = np.zeros((len(paths), EMBED_DIM), dtype=np.float32)
    for i, p in enumerate(paths):
        out[i] = embed_audio_file(p)
        if log_every and (i + 1) % log_every == 0:
            print(f"  embedded {i + 1}/{len(paths)}", flush=True)
    return out


@torch.no_grad()
def embed_text(texts: list[str]) -> np.ndarray:
    """Embed text prompts into the same 512-d space. Returns (N, 512) normalised."""
    model, processor = _load_model()
    inputs = processor(text=texts, return_tensors="pt", padding=True)
    feats = model.get_text_features(**inputs).cpu().numpy()
    return _l2_normalize(feats)


if __name__ == "__main__":
    # Smoke test: embed a couple of DEAM clips + a text prompt, check shapes and
    # that audio<->text cosine similarities are sane.
    from emotion.deam import load_deam_manifest

    mani = load_deam_manifest().head(3)
    print("Embedding 3 DEAM clips...")
    aud = embed_audio_files(mani["audio_path"].tolist(), log_every=0)
    print("audio embeddings:", aud.shape, "norm~", round(float(np.linalg.norm(aud[0])), 3))

    txt = embed_text(["a happy upbeat song", "a sad slow song"])
    print("text embeddings:", txt.shape)
    print("cosine(audio0, 'happy'):", round(float(aud[0] @ txt[0]), 3))
    print("cosine(audio0, 'sad'):  ", round(float(aud[0] @ txt[1]), 3))
