"""Offline pipeline: precompute CLAP embeddings for the DEAM corpus.

This is the expensive step, and the whole point of the architecture is that it
runs ONCE, offline, never per request. The output (.npz of embeddings + aligned
valence/arousal targets) feeds both the regression head (Phase 1 training) and
the recommendation index. Serving only ever does cheap vector math on top.

CRASH-SAFE / RESUMABLE: every clip's embedding is written to its own .npy under a
cache dir the moment it's computed. Re-running skips clips already on disk, so a
laptop sleeping, a crash, or a Ctrl-C costs at most one clip — never the whole run.
The final step consolidates the per-clip files into one .npz in manifest order.

Usage:
    PYTHONPATH=src python -m emotion.build_embeddings              # all clips (resumes)
    PYTHONPATH=src python -m emotion.build_embeddings --limit 20   # quick timing
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np

from emotion.deam import load_deam_manifest
from emotion.embed import EMBED_DIM, embed_audio_file

DEFAULT_OUT = Path("artifacts/deam/deam_clap.npz")


def _cache_dir(out: Path) -> Path:
    return out.parent / f"{out.stem}_cache"


def build(out: Path, limit: int | None = None, log_every: int = 25) -> None:
    mani = load_deam_manifest()
    if limit:
        mani = mani.head(limit)
    n = len(mani)

    cache = _cache_dir(out)
    cache.mkdir(parents=True, exist_ok=True)

    already = sum(1 for s in mani["song_id"] if (cache / f"{s}.npy").is_file())
    print(f"{n} clips total · {already} already cached · {n - already} to do", flush=True)

    t0 = time.time()
    done_this_run = 0
    for i, row in enumerate(mani.itertuples(index=False)):
        f = cache / f"{row.song_id}.npy"
        if f.is_file():
            continue  # resume: skip clips already embedded
        emb = embed_audio_file(row.audio_path)
        # Write atomically (tmp then replace) so a crash mid-write can't leave a
        # half-written .npy that later loads as garbage.
        tmp = f.with_suffix(".npy.tmp")
        np.save(tmp, emb)
        tmp.replace(f)
        done_this_run += 1
        if log_every and done_this_run % log_every == 0:
            rate = done_this_run / (time.time() - t0)
            remaining = (n - i - 1)
            print(f"  {i + 1}/{n}  ({rate:.2f} clips/s, ETA {remaining / rate / 60:.1f} min)",
                  flush=True)

    consolidate(out, mani)


def consolidate(out: Path, mani=None) -> None:
    """Stack all cached per-clip embeddings into one .npz, in manifest order."""
    if mani is None:
        mani = load_deam_manifest()
    cache = _cache_dir(out)

    X = np.zeros((len(mani), EMBED_DIM), dtype=np.float32)
    missing = []
    for i, s in enumerate(mani["song_id"]):
        f = cache / f"{s}.npy"
        if f.is_file():
            X[i] = np.load(f)
        else:
            missing.append(int(s))
    if missing:
        print(f"WARNING: {len(missing)} clips still missing (e.g. {missing[:5]}). "
              f"Re-run to finish before training.", flush=True)
        return

    np.savez_compressed(
        out,
        X=X,
        song_id=mani["song_id"].to_numpy(),
        valence=mani["valence"].to_numpy(np.float32),
        arousal=mani["arousal"].to_numpy(np.float32),
        valence_mean=mani["valence_mean"].to_numpy(np.float32),
        arousal_mean=mani["arousal_mean"].to_numpy(np.float32),
    )
    print(f"Consolidated {len(mani)} clips -> {out}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--consolidate-only", action="store_true",
                    help="just stack existing cached clips into the .npz")
    args = ap.parse_args()
    if args.consolidate_only:
        consolidate(args.out)
    else:
        build(args.out, limit=args.limit)
