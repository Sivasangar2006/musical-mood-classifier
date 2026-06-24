"""Offline pipeline: build the recommendation corpus from iTunes previews.

Recommendations work by embedding a query song and finding its nearest neighbours
in a corpus of *recognizable, streamable* tracks. We build that corpus here: search
iTunes across a spread of moods/genres/eras, download each 30 s preview, embed it
with CLAP, predict its valence/arousal, and cache everything.

Like build_embeddings, this is CRASH-SAFE / RESUMABLE: each track is cached to its
own .npz the moment it's processed, so a sleep/crash costs at most one track. The
consolidate step stacks them into one corpus file the recommender loads at startup.

Usage:
    PYTHONPATH=src python -m emotion.build_itunes_corpus                 # full build
    PYTHONPATH=src python -m emotion.build_itunes_corpus --per-query 5   # quick test
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
import uuid
from pathlib import Path

import httpx
import numpy as np

from emotion.predict_va import analyze_audio

OUT_DIR = Path("artifacts/corpus")
TRACK_CACHE = OUT_DIR / "itunes"            # per-track .npz cache
CORPUS_NPZ = OUT_DIR / "itunes_corpus.npz"  # consolidated embeddings + V/A
CORPUS_META = OUT_DIR / "itunes_meta.json"  # consolidated track metadata

# A deliberately broad query set so the corpus spans the whole emotion plane, not
# just the five mood playlists — genres, eras and energy levels all differ in V/A.
QUERIES = [
    "happy pop hits", "feel good songs", "upbeat summer", "good vibes",
    "workout pump up", "high energy dance", "edm festival", "rock anthems",
    "heavy metal", "metalcore aggressive", "punk rock", "hard rock",
    "sad songs heartbreak", "emotional ballad", "melancholy indie", "breakup songs",
    "chill lofi", "calm piano", "relaxing ambient", "acoustic covers",
    "90s pop classics", "80s hits", "disco classics", "motown soul",
    "rnb slow jams", "rap hits", "indie folk", "country roads",
    "jazz standards", "classical piano", "blues guitar", "reggae chill",
    "epic soundtrack", "synthwave retro",
]

ITUNES = "https://itunes.apple.com/search"


def gather_tracks(per_query: int) -> dict[int, dict]:
    """Search iTunes across all queries and return de-duplicated tracks with previews."""
    tracks: dict[int, dict] = {}
    with httpx.Client(timeout=15.0) as client:
        for q in QUERIES:
            try:
                resp = client.get(ITUNES, params={
                    "term": q, "media": "music", "entity": "song", "limit": per_query,
                })
                resp.raise_for_status()
            except httpx.HTTPError as e:
                print(f"  [warn] query '{q}' failed: {e}", flush=True)
                continue
            for t in resp.json().get("results", []):
                if t.get("kind") == "song" and t.get("previewUrl") and t.get("trackId"):
                    tid = int(t["trackId"])
                    if tid not in tracks:
                        tracks[tid] = {
                            "id": tid,
                            "title": t.get("trackName", ""),
                            "artist": t.get("artistName", ""),
                            "album_art": t.get("artworkUrl100", ""),
                            "preview_url": t["previewUrl"],
                            "store_url": t.get("trackViewUrl", ""),
                            "genre": t.get("primaryGenreName", ""),
                            "seed_query": q,
                        }
    return tracks


def _process_one(meta: dict, client: httpx.Client) -> None:
    """Download + embed + V/A one track, caching to its own .npz."""
    cache_f = TRACK_CACHE / f"{meta['id']}.npz"
    if cache_f.is_file():
        return
    tmp = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.m4a")
    try:
        r = client.get(meta["preview_url"], timeout=20.0, follow_redirects=True)
        r.raise_for_status()
        with open(tmp, "wb") as f:
            f.write(r.content)
        res = analyze_audio(tmp)
        np.savez(
            cache_f,
            emb=np.asarray(res["embedding"], dtype=np.float32),
            valence=np.float32(res["valence"]),
            arousal=np.float32(res["arousal"]),
        )
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def build(per_query: int, log_every: int = 20) -> None:
    TRACK_CACHE.mkdir(parents=True, exist_ok=True)
    print("Gathering tracks from iTunes...", flush=True)
    tracks = gather_tracks(per_query)
    (OUT_DIR / "itunes_tracks.json").write_text(json.dumps(tracks, indent=2), encoding="utf-8")
    n = len(tracks)
    cached = sum(1 for tid in tracks if (TRACK_CACHE / f"{tid}.npz").is_file())
    print(f"{n} unique tracks · {cached} already cached · {n - cached} to do", flush=True)

    t0 = time.time()
    done = 0
    with httpx.Client() as client:
        for i, meta in enumerate(tracks.values()):
            if (TRACK_CACHE / f"{meta['id']}.npz").is_file():
                continue
            try:
                _process_one(meta, client)
            except Exception as e:  # noqa: BLE001 — skip a bad track, never abort the run
                print(f"  [skip] {meta['title'][:30]}: {e}", flush=True)
                continue
            done += 1
            if log_every and done % log_every == 0:
                rate = done / (time.time() - t0)
                print(f"  {i + 1}/{n} ({rate:.2f} tracks/s, ETA {(n - i - 1)/rate/60:.1f} min)",
                      flush=True)
    consolidate()


# Royalty-free "mood music" (Sound Therapy Music, Deep Sleep Music, etc.) pollutes
# text search because pure-mood audio has unnaturally strong text affinity. Drop it.
_GENERIC_ARTIST = [
    "relaxing", "meditation", "lullaby", "sound therapy", "deep sleep", "sleep music",
    "white noise", "nature sound", "study music", "zen", "spa", "healing", "wellness",
    "ambient", "instrumental", "peaceful", "royalty", "background music", "sleep aid",
    "detox", "soothing", "calm ", "piano relax", "relax", "lofi", "study",
]
_GENERIC_TITLES = {q.lower() for q in QUERIES} | {
    "feel good songs", "high-energy dance", "high energy dance", "relaxing ambient",
    "calm piano", "jazz standards", "chill lofi", "epic soundtrack", "blues guitar",
    "heavy metal", "edm festival", "reggae chill", "classical piano", "synthwave retro",
}


_GENERIC_TITLE_SUBSTR = ["backing track", "karaoke", "instrumental", "(from \"", "lullaby", "white noise"]


def _is_generic(m: dict) -> bool:
    title = m["title"].lower().strip()
    artist = m["artist"].lower()
    if title in _GENERIC_TITLES:
        return True
    if any(s in title for s in _GENERIC_TITLE_SUBSTR):
        return True
    return any(g in artist for g in _GENERIC_ARTIST)


def consolidate() -> None:
    """Stack cached tracks into one corpus .npz + metadata json the recommender loads.
    Generic royalty-free mood music is filtered out (see _is_generic)."""
    tracks = json.loads((OUT_DIR / "itunes_tracks.json").read_text(encoding="utf-8"))
    rows, meta = [], []
    dropped = 0
    seen_songs = set()  # dedupe same song appearing under multiple track ids
    for tid, m in tracks.items():
        f = TRACK_CACHE / f"{tid}.npz"
        if not f.is_file():
            continue
        if _is_generic(m):
            dropped += 1
            continue
        key = (m["title"].lower().strip(), m["artist"].lower().strip())
        if key in seen_songs:
            dropped += 1
            continue
        seen_songs.add(key)
        d = np.load(f)
        rows.append((d["emb"], float(d["valence"]), float(d["arousal"])))
        meta.append({**m, "valence": float(d["valence"]), "arousal": float(d["arousal"])})
    if not rows:
        print("No cached tracks to consolidate yet.", flush=True)
        return
    X = np.stack([r[0] for r in rows]).astype(np.float32)
    valence = np.array([r[1] for r in rows], dtype=np.float32)
    arousal = np.array([r[2] for r in rows], dtype=np.float32)
    np.savez_compressed(CORPUS_NPZ, X=X, valence=valence, arousal=arousal,
                        track_id=np.array([m["id"] for m in meta]))
    CORPUS_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Consolidated {len(meta)} tracks ({dropped} generic dropped) "
          f"-> {CORPUS_NPZ} (+ {CORPUS_META.name})", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-query", type=int, default=25, help="iTunes results per search term")
    ap.add_argument("--consolidate-only", action="store_true")
    args = ap.parse_args()
    if args.consolidate_only:
        consolidate()
    else:
        build(args.per_query)
