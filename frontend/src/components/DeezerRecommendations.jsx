/**
 * DeezerRecommendations
 * Shows mood-based song recommendations from Deezer with inline 30s previews.
 * Also lets the user search for any song in the world.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { Loader2, Search, Play, Pause, ExternalLink, RefreshCw } from 'lucide-react';
import { getRecommendations, searchTracks } from '../api/client.js';

const MOOD_COLOR = {
  Happy:     { ring: 'ring-yellow-500',  bg: 'bg-yellow-500',  text: 'text-yellow-400' },
  Energetic: { ring: 'ring-red-500',     bg: 'bg-red-500',     text: 'text-red-400'    },
  Angry:     { ring: 'ring-purple-500',  bg: 'bg-purple-500',  text: 'text-purple-400' },
  Sad:       { ring: 'ring-blue-500',    bg: 'bg-blue-500',    text: 'text-blue-400'   },
  Relaxed:   { ring: 'ring-emerald-500', bg: 'bg-emerald-500', text: 'text-emerald-400'},
};

function TrackRow({ track, isPlaying, onToggle }) {
  const colors = MOOD_COLOR;   // accessed via parent's mood context; use neutral here

  return (
    <div className="flex items-center gap-3 p-3 rounded-xl bg-gray-800/50 hover:bg-gray-800
                    transition-colors group">
      {/* Album art */}
      <div className="relative shrink-0">
        {track.album_art ? (
          <img
            src={track.album_art}
            alt={track.album}
            className="w-12 h-12 rounded-lg object-cover"
          />
        ) : (
          <div className="w-12 h-12 rounded-lg bg-gray-700 flex items-center justify-center">
            <span className="text-gray-500 text-lg">♪</span>
          </div>
        )}

        {/* Play overlay on album art */}
        {track.preview_url && (
          <button
            onClick={() => onToggle(track)}
            className="absolute inset-0 rounded-lg bg-black/50 opacity-0 group-hover:opacity-100
                       flex items-center justify-center transition-opacity"
          >
            {isPlaying
              ? <Pause className="w-5 h-5 text-white" />
              : <Play  className="w-5 h-5 text-white ml-0.5" />}
          </button>
        )}
      </div>

      {/* Track info */}
      <div className="flex-1 min-w-0">
        <p className="text-white text-sm font-medium truncate">{track.title}</p>
        <p className="text-gray-400 text-xs truncate">{track.artist}</p>
        {track.preview_url && (
          <div className="mt-1">
            {isPlaying ? (
              /* waveform-style "now playing" indicator */
              <div className="flex items-end gap-0.5 h-3">
                {[1,2,3,4].map(i => (
                  <div
                    key={i}
                    className="w-0.5 bg-violet-400 rounded-full animate-pulse"
                    style={{
                      height: `${40 + i * 15}%`,
                      animationDelay: `${i * 0.15}s`,
                      animationDuration: '0.8s',
                    }}
                  />
                ))}
                <span className="text-violet-400 text-[10px] ml-1">playing</span>
              </div>
            ) : (
              <span className="text-gray-600 text-[10px]">30s preview</span>
            )}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 shrink-0">
        {track.preview_url && (
          <button
            onClick={() => onToggle(track)}
            className="w-8 h-8 rounded-full bg-gray-700 hover:bg-violet-600
                       flex items-center justify-center transition-colors"
          >
            {isPlaying
              ? <Pause className="w-3.5 h-3.5 text-white" />
              : <Play  className="w-3.5 h-3.5 text-white ml-0.5" />}
          </button>
        )}
        <a
          href={track.store_url || track.deezer_url}
          target="_blank"
          rel="noopener noreferrer"
          className="w-8 h-8 rounded-full bg-gray-700 hover:bg-gray-600
                     flex items-center justify-center transition-colors"
          title="Open in Apple Music"
        >
          <ExternalLink className="w-3.5 h-3.5 text-gray-400" />
        </a>
      </div>
    </div>
  );
}


export default function DeezerRecommendations({ mood }) {
  const [tracks,  setTracks]  = useState([]);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);
  const [query,   setQuery]   = useState('');
  const [searching, setSearching] = useState(false);
  const [offset,  setOffset]  = useState(0);

  // Single shared audio element
  const audioRef    = useRef(new Audio());
  const [playingId, setPlayingId] = useState(null);

  const fetchRecommendations = useCallback(async (newOffset = 0) => {
    if (!mood) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getRecommendations(mood, 8, newOffset);
      setTracks(data.tracks);
      setOffset(newOffset);
    } catch {
      setError('Could not load recommendations. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, [mood]);

  useEffect(() => {
    fetchRecommendations(0);
    return () => {
      audioRef.current.pause();
      audioRef.current.src = '';
    };
  }, [fetchRecommendations]);

  // Stop audio when mood changes
  useEffect(() => {
    audioRef.current.pause();
    setPlayingId(null);
  }, [mood]);

  const handleToggle = (track) => {
    const audio = audioRef.current;

    if (playingId === track.id) {
      audio.pause();
      setPlayingId(null);
      return;
    }

    audio.pause();
    audio.src = track.preview_url;
    audio.play().catch(() => {});
    setPlayingId(track.id);

    audio.onended = () => setPlayingId(null);
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) { fetchRecommendations(0); return; }
    setSearching(true);
    setError(null);
    try {
      const data = await searchTracks(mood, query.trim());
      setTracks(data.tracks);
    } catch {
      setError('Search failed.');
    } finally {
      setSearching(false);
    }
  };

  const handleRefresh = () => {
    setQuery('');
    fetchRecommendations(offset + 8);
  };

  const colors = MOOD_COLOR[mood] || MOOD_COLOR.Happy;

  return (
    <div className="mt-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <p className="text-gray-500 text-xs uppercase tracking-widest font-semibold">
            Songs You Might Like
          </p>
          <p className="text-gray-700 text-xs mt-0.5">Powered by iTunes · 30s previews</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="flex items-center gap-1.5 text-gray-600 hover:text-gray-300
                     text-xs transition-colors disabled:opacity-40"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          More
        </button>
      </div>

      {/* Search bar */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-600" />
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search any song or artist…"
            className="w-full pl-9 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg
                       text-white text-sm placeholder-gray-600
                       focus:outline-none focus:border-gray-500 transition-colors"
          />
        </div>
        <button
          type="submit"
          disabled={searching}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors
            ${colors.bg} text-white hover:opacity-90 disabled:opacity-50`}
        >
          {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Search'}
        </button>
      </form>

      {/* Track list */}
      {loading ? (
        <div className="flex items-center gap-2 text-gray-500 text-sm py-6 justify-center">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>Finding {mood?.toLowerCase()} tracks…</span>
        </div>
      ) : error ? (
        <p className="text-red-400 text-sm text-center py-4">{error}</p>
      ) : tracks.length === 0 ? (
        <p className="text-gray-600 text-sm text-center py-4">No tracks found.</p>
      ) : (
        <div className="space-y-2">
          {tracks.map(track => (
            <TrackRow
              key={track.id}
              track={track}
              isPlaying={playingId === track.id}
              onToggle={handleToggle}
            />
          ))}
        </div>
      )}

      {/* Currently playing indicator */}
      {playingId && (
        <div className="mt-3 flex items-center justify-between text-xs text-gray-600
                        bg-gray-800/30 rounded-lg px-3 py-2">
          <span>Playing 30s preview</span>
          <button
            onClick={() => { audioRef.current.pause(); setPlayingId(null); }}
            className="text-gray-500 hover:text-white transition-colors"
          >
            Stop
          </button>
        </div>
      )}
    </div>
  );
}
