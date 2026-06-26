/**
 * CorpusTracks — a playable list of recommended tracks.
 * Reused for "similar songs" and the mood/vibe browsers.
 * Each track: { id, title, artist, album_art, preview_url, store_url, score? }
 */

import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { Play, Pause, ExternalLink } from 'lucide-react';
import { stagger, item } from '../lib/motion.js';

export default function CorpusTracks({ tracks = [], heading, subheading, accent = '#C2553A' }) {
  const audioRef = useRef(null);
  const [playingId, setPlayingId] = useState(null);

  useEffect(() => {
    audioRef.current = new Audio();
    const a = audioRef.current;
    return () => { a.pause(); a.src = ''; };
  }, []);

  const toggle = (track) => {
    const a = audioRef.current;
    if (!a) return;
    if (playingId === track.id) { a.pause(); setPlayingId(null); return; }
    a.pause();
    a.src = track.preview_url;
    a.play().catch(() => {});
    a.onended = () => setPlayingId(null);
    setPlayingId(track.id);
  };

  if (!tracks.length) return null;

  return (
    <div>
      {heading && (
        <div className="mb-3">
          <p className="text-ink text-sm font-semibold">{heading}</p>
          {subheading && <p className="text-ink-soft text-xs mt-0.5">{subheading}</p>}
        </div>
      )}
      <motion.div variants={stagger} initial="hidden" animate="show" className="space-y-1.5">
        {tracks.map((track) => {
          const isPlaying = playingId === track.id;
          return (
            <motion.div
              key={track.id}
              variants={item}
              className="flex items-center gap-3 p-2 rounded-lg hover:bg-paper transition-colors group"
            >
              <button onClick={() => toggle(track)} className="relative shrink-0 cursor-pointer">
                {track.album_art ? (
                  <img src={track.album_art} alt="" className="w-11 h-11 rounded-md object-cover border border-line" />
                ) : (
                  <div className="w-11 h-11 rounded-md bg-paper border border-line flex items-center justify-center text-ink-faint">♪</div>
                )}
                {track.preview_url && (
                  <span className={`absolute inset-0 rounded-md bg-black/45 flex items-center justify-center transition-opacity
                                    ${isPlaying ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}>
                    {isPlaying ? <Pause className="w-4 h-4 text-white" /> : <Play className="w-4 h-4 text-white ml-0.5" />}
                  </span>
                )}
              </button>

              <div className="flex-1 min-w-0">
                <p className="text-ink text-sm font-medium truncate">{track.title}</p>
                <p className="text-ink-soft text-xs truncate">{track.artist}</p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                {typeof track.score === 'number' && (
                  <span className="text-[11px] font-medium px-1.5 py-0.5 rounded"
                    style={{ color: accent, background: `${accent}14` }}>
                    {Math.round(track.score * 100)}%
                  </span>
                )}
                {track.store_url && (
                  <a href={track.store_url} target="_blank" rel="noopener noreferrer"
                    className="w-8 h-8 rounded-lg border border-line text-ink-soft hover:text-ink hover:border-line-strong
                               flex items-center justify-center transition-colors opacity-0 group-hover:opacity-100"
                    title="Open in store">
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
            </motion.div>
          );
        })}
      </motion.div>
    </div>
  );
}
