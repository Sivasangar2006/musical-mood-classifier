"""Recommendation engine over the iTunes corpus.

Two recommendation modes, both cheap vector math on the precomputed corpus:

  1. similar-to-song : cosine nearest-neighbours of a query CLAP embedding. "You
     analysed X — here are songs that *feel* like it." Captures timbre/mood/energy
     beyond what a single mood label could.
  2. by-mood / by-point : tracks nearest a target valence/arousal point. Powers the
     "pick a mood -> get N songs" browse flow, replacing the old hardcoded lists.

The corpus is ~800 L2-normalised vectors, so a plain NumPy matmul is instant — no
vector DB needed at this scale (pgvector would be premature ops complexity).
"""

from __future__ import annotations

import functools
import json

import numpy as np

from emotion.embed import embed_text
from emotion.predict_va import MOOD_ANCHORS, _REPO_ROOT

CORPUS_NPZ = _REPO_ROOT / "artifacts" / "corpus" / "itunes_corpus.npz"
CORPUS_META = _REPO_ROOT / "artifacts" / "corpus" / "itunes_meta.json"


@functools.lru_cache(maxsize=1)
def _load_corpus():
    if not CORPUS_NPZ.is_file():
        raise FileNotFoundError(
            f"Corpus not found at {CORPUS_NPZ}. Run `python -m emotion.build_itunes_corpus`."
        )
    d = np.load(CORPUS_NPZ)
    meta = json.loads(CORPUS_META.read_text(encoding="utf-8"))
    X = d["X"].astype(np.float32)              # already L2-normalised at build time
    return X, d["valence"], d["arousal"], d["track_id"], meta


def corpus_size() -> int:
    return len(_load_corpus()[4])


def recommend_similar(embedding, k: int = 10, exclude_id: int | None = None) -> list[dict]:
    """Top-k corpus tracks by cosine similarity to a query embedding."""
    X, _, _, tid, meta = _load_corpus()
    q = np.asarray(embedding, dtype=np.float32)
    q = q / np.clip(np.linalg.norm(q), 1e-8, None)
    sims = X @ q                                # cosine, since rows are unit-norm
    out = []
    for i in np.argsort(-sims):
        if exclude_id is not None and int(tid[i]) == int(exclude_id):
            continue
        out.append({**meta[i], "score": round(float(sims[i]), 3)})
        if len(out) >= k:
            break
    return out


def recommend_by_va(valence: float, arousal: float, k: int = 15) -> list[dict]:
    """Top-k corpus tracks nearest a target (valence, arousal) point."""
    X, v, a, tid, meta = _load_corpus()
    dist = (v - valence) ** 2 + (a - arousal) ** 2
    order = np.argsort(dist)[:k]
    return [{**meta[i], "distance": round(float(np.sqrt(dist[i])), 3)} for i in order]


def recommend_by_text(query: str, k: int = 15) -> list[dict]:
    """Cross-modal search: rank corpus songs by CLAP similarity to a text vibe.

    Because CLAP embeds audio and text into the same space, a free-text prompt like
    "rainy sunday morning" or "angry workout rage" retrieves songs that *sound* like
    that description — no tags, no keyword matching.
    """
    X, _, _, _, meta = _load_corpus()
    q = embed_text([query])[0]
    q = q / np.clip(np.linalg.norm(q), 1e-8, None)
    sims = X @ q
    order = np.argsort(-sims)[:k]
    return [{**meta[i], "score": round(float(sims[i]), 3)} for i in order]


def recommend_by_mood(mood: str, k: int = 15) -> list[dict]:
    """Top-k corpus tracks for a named mood (its circumplex anchor point)."""
    if mood not in MOOD_ANCHORS:
        raise ValueError(f"Unknown mood {mood!r}; use one of {list(MOOD_ANCHORS)}")
    val, ar = MOOD_ANCHORS[mood]
    return recommend_by_va(val, ar, k)


if __name__ == "__main__":
    print(f"Corpus: {corpus_size()} tracks\n")
    for mood in MOOD_ANCHORS:
        recs = recommend_by_mood(mood, k=3)
        print(f"{mood}:")
        for r in recs:
            print(f"   {r['title'][:30]:30} - {r['artist'][:18]:18} "
                  f"(V={r['valence']:+.2f} A={r['arousal']:+.2f})")
