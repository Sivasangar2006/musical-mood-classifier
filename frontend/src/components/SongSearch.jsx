/**
 * SongSearch
 * The core product flow: search iTunes for a song, pick one, and analyse its
 * emotion with the CLAP valence/arousal engine.
 */

import { useState } from 'react';
import { Search, Loader2, Sparkles } from 'lucide-react';
import { searchSongs, analyzeTrack } from '../api/client.js';
import MusicLoader from './MusicLoader.jsx';

export default function SongSearch({ onResult }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [analyzing, setAnalyzing] = useState(null); // track being analysed
  const [error, setError] = useState(null);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true); setError(null); setResults([]);
    try {
      const tracks = await searchSongs(query.trim(), 10);
      setResults(tracks.filter((t) => t.preview_url));
      if (!tracks.length) setError('No songs found. Try another search.');
    } catch {
      setError('Search failed. Is the backend running?');
    } finally {
      setSearching(false);
    }
  };

  const handleSelect = async (track) => {
    setAnalyzing(track); setError(null);
    try {
      const result = await analyzeTrack(track);
      onResult(result, track);
    } catch (err) {
      setError(err.response?.data?.detail || 'Analysis failed. Is the backend running?');
      setAnalyzing(null);
    }
  };

  if (analyzing) {
    return (
      <div className="card p-10 max-w-xl mx-auto animate-scale-in">
        <MusicLoader text={`Analysing "${analyzing.title}"…`} />
        <p className="text-center text-gray-600 text-xs mt-3">
          Running CLAP + valence/arousal model on the 30s preview
        </p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-xl mx-auto animate-fade-in-up">
      <form onSubmit={handleSearch} className="flex gap-2">
        <div className="flex-1 relative">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search a song to analyse — e.g. Shape of You"
            className="w-full pl-10 pr-3 py-3.5 bg-gray-900 border border-gray-700 rounded-xl
                       text-white placeholder-gray-600 focus:outline-none focus:border-violet-500 transition-colors"
          />
        </div>
        <button type="submit" disabled={searching}
          className="px-5 py-3.5 rounded-xl bg-violet-600 hover:bg-violet-500 text-white font-semibold transition-colors disabled:opacity-50">
          {searching ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Search'}
        </button>
      </form>

      {error && <p className="text-red-400 text-sm text-center mt-3">{error}</p>}

      {results.length > 0 && (
        <div className="mt-4 space-y-2">
          {results.map((track) => (
            <button key={track.id} onClick={() => handleSelect(track)}
              className="w-full flex items-center gap-3 p-3 rounded-xl bg-gray-900 border border-gray-800
                         hover:border-violet-600 hover:bg-gray-800/80 transition-all text-left group">
              {track.album_art
                ? <img src={track.album_art} alt={track.title} className="w-12 h-12 rounded-lg object-cover shrink-0" />
                : <div className="w-12 h-12 rounded-lg bg-gray-700 flex items-center justify-center shrink-0 text-gray-500">♪</div>}
              <div className="flex-1 min-w-0">
                <p className="text-white text-sm font-medium truncate">{track.title}</p>
                <p className="text-gray-400 text-xs truncate">{track.artist}</p>
              </div>
              <span className="flex items-center gap-1 text-violet-400 text-xs font-medium opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                <Sparkles className="w-3.5 h-3.5" /> Analyse
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
