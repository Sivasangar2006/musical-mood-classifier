/**
 * CorpusTracks
 * A self-contained, playable list of tracks from the CLAP recommendation corpus.
 * Reused for "similar songs" (after analysing a song) and the mood browser.
 * Each track: { id, title, artist, album_art, preview_url, store_url, score? }
 */

import { useEffect, useRef, useState } from 'react';
import { Play, Pause, ExternalLink } from 'lucide-react';

export default function CorpusTracks({ tracks = [], heading, subheading, accent = '#7c3aed' }) {
  const audioRef = useRef(null);
  const [playingId, setPlayingId] = useState(null);

  // Lazily create one shared audio element
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
    <div className="mt-6">
      {heading && (
        <div className="mb-3">
          <p className="text-gray-500 text-xs uppercase tracking-widest font-semibold">{heading}</p>
          {subheading && <p className="text-gray-700 text-xs mt-0.5">{subheading}</p>}
        </div>
      )}
      <div className="space-y-2">
        {tracks.map((track) => {
          const isPlaying = playingId === track.id;
          return (
            <div key={track.id}
              className="flex items-center gap-3 p-3 rounded-xl bg-gray-800/50 hover:bg-gray-800 transition-colors group">
              <div className="relative shrink-0">
                {track.album_art ? (
                  <img src={track.album_art} alt={track.title} className="w-12 h-12 rounded-lg object-cover" />
                ) : (
                  <div className="w-12 h-12 rounded-lg bg-gray-700 flex items-center justify-center text-gray-500 text-lg">♪</div>
                )}
                {track.preview_url && (
                  <button onClick={() => toggle(track)}
                    className="absolute inset-0 rounded-lg bg-black/50 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                    {isPlaying ? <Pause className="w-5 h-5 text-white" /> : <Play className="w-5 h-5 text-white ml-0.5" />}
                  </button>
                )}
              </div>

              <div className="flex-1 min-w-0">
                <p className="text-white text-sm font-medium truncate">{track.title}</p>
                <p className="text-gray-400 text-xs truncate">{track.artist}</p>
                {isPlaying && <span className="text-violet-400 text-[10px]">▶ playing 30s preview</span>}
              </div>

              <div className="flex items-center gap-2 shrink-0">
                {typeof track.score === 'number' && (
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                    style={{ color: accent, background: `${accent}1a` }}>
                    {Math.round(track.score * 100)}%
                  </span>
                )}
                {track.preview_url && (
                  <button onClick={() => toggle(track)}
                    className="w-8 h-8 rounded-full bg-gray-700 hover:bg-violet-600 flex items-center justify-center transition-colors">
                    {isPlaying ? <Pause className="w-3.5 h-3.5 text-white" /> : <Play className="w-3.5 h-3.5 text-white ml-0.5" />}
                  </button>
                )}
                {track.store_url && (
                  <a href={track.store_url} target="_blank" rel="noopener noreferrer"
                    className="w-8 h-8 rounded-full bg-gray-700 hover:bg-gray-600 flex items-center justify-center transition-colors"
                    title="Open in Apple Music">
                    <ExternalLink className="w-3.5 h-3.5 text-gray-400" />
                  </a>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
