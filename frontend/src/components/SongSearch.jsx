/**
 * SongSearch — live typeahead. Suggests songs as you type (debounced), pick one
 * to read its mood. No submit button, no jargon.
 */

import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Search, Loader2, ArrowRight } from 'lucide-react';
import { searchSongs, analyzeTrack } from '../api/client.js';
import { popover } from '../lib/motion.js';
import MusicLoader from './MusicLoader.jsx';

export default function SongSearch({ onResult }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [analyzing, setAnalyzing] = useState(null);
  const [error, setError] = useState(null);
  const boxRef = useRef(null);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) { setResults([]); setOpen(false); return; }
    setLoading(true);
    const t = setTimeout(async () => {
      try {
        const tracks = await searchSongs(q, 8);
        setResults(tracks.filter((x) => x.preview_url));
        setOpen(true);
      } catch {
        setError('Search is unavailable right now. Please try again.');
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => clearTimeout(t);
  }, [query]);

  useEffect(() => {
    const onClick = (e) => { if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const handleSelect = async (track) => {
    setOpen(false); setAnalyzing(track); setError(null);
    try {
      const result = await analyzeTrack(track);
      onResult(result, track);
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not analyse that track. Please try another.');
      setAnalyzing(null);
    }
  };

  if (analyzing) {
    return (
      <div className="card p-10 max-w-xl mx-auto">
        <MusicLoader text={`Listening to “${analyzing.title}”…`} />
      </div>
    );
  }

  return (
    <div ref={boxRef} className="w-full max-w-xl mx-auto relative">
      <div className="relative">
        {loading
          ? <Loader2 className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-clay animate-spin" />
          : <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-ink-faint" strokeWidth={2} />}
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length && setOpen(true)}
          placeholder="Search a song or artist…"
          className="w-full pl-12 pr-4 h-14 bg-card border border-line-strong rounded-xl2 text-ink text-base
                     placeholder-ink-faint shadow-card focus:outline-none focus:border-clay
                     focus:ring-2 focus:ring-clay/20 transition-shadow"
        />
      </div>

      {error && <p className="text-energetic text-sm text-center mt-3">{error}</p>}

      <AnimatePresence>
        {open && results.length > 0 && (
          <motion.div
            variants={popover} initial="hidden" animate="show" exit="exit"
            className="absolute z-30 mt-2 w-full bg-card border border-line rounded-xl2 overflow-hidden shadow-pop"
          >
            {results.map((track) => (
              <button
                key={track.id}
                onClick={() => handleSelect(track)}
                className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-paper transition-colors text-left
                           group cursor-pointer border-b border-line last:border-0"
              >
                {track.album_art
                  ? <img src={track.album_art} alt="" className="w-10 h-10 rounded-md object-cover shrink-0 border border-line" />
                  : <div className="w-10 h-10 rounded-md bg-paper border border-line flex items-center justify-center shrink-0 text-ink-faint text-sm">♪</div>}
                <div className="flex-1 min-w-0">
                  <p className="text-ink text-sm font-medium truncate">{track.title}</p>
                  <p className="text-ink-soft text-xs truncate">{track.artist}</p>
                </div>
                <ArrowRight
                  className="w-4 h-4 text-clay opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0
                             transition-all shrink-0"
                  strokeWidth={2.25}
                />
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
