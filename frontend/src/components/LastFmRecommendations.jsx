/**
 * LastFmRecommendations
 * Fetches and displays mood-tagged tracks from the Last.fm API.
 * Requires VITE_LASTFM_API_KEY to be set; renders nothing when absent.
 */

import { useEffect, useState } from 'react';
import { Loader2, ExternalLink } from 'lucide-react';
import { getTracksForMood } from '../api/lastfm.js';

const HAS_KEY = !!import.meta.env.VITE_LASTFM_API_KEY;

export default function LastFmRecommendations({ mood }) {
  const [tracks, setTracks]   = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!mood || !HAS_KEY) return;
    setLoading(true);
    getTracksForMood(mood)
      .then(setTracks)
      .catch(() => setTracks([]))
      .finally(() => setLoading(false));
  }, [mood]);

  if (!HAS_KEY) {
    return (
      <div className="mt-8">
        <p className="text-gray-500 text-xs uppercase tracking-widest font-semibold mb-3">
          Recommended Tracks
        </p>
        <p className="text-gray-700 text-xs">
          Add{' '}
          <code className="bg-gray-800 px-1 rounded">VITE_LASTFM_API_KEY</code>{' '}
          to enable Last.fm recommendations.
        </p>
      </div>
    );
  }

  return (
    <div className="mt-8">
      <p className="text-gray-500 text-xs uppercase tracking-widest font-semibold mb-4">
        Recommended Tracks
      </p>

      {loading ? (
        <div className="flex items-center gap-2 text-gray-500 text-sm py-4">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>Finding {mood} tracks…</span>
        </div>
      ) : tracks.length === 0 ? (
        <p className="text-gray-700 text-sm">No tracks found.</p>
      ) : (
        <div className="space-y-2">
          {tracks.map((track, i) => (
            <a
              key={i}
              href={track.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 bg-gray-800/50 rounded-xl px-4 py-2.5
                         hover:bg-gray-800 transition-colors group"
            >
              {/* Album art */}
              {track.image ? (
                <img
                  src={track.image}
                  alt=""
                  className="w-9 h-9 rounded-lg object-cover shrink-0"
                />
              ) : (
                <div className="w-9 h-9 rounded-lg bg-gray-700 shrink-0 flex items-center justify-center">
                  <span className="text-gray-500 text-xs">♪</span>
                </div>
              )}

              {/* Track info */}
              <div className="flex-1 min-w-0">
                <p className="text-white text-sm font-medium truncate">{track.name}</p>
                <p className="text-gray-500 text-xs truncate">{track.artist}</p>
              </div>

              <ExternalLink className="w-3.5 h-3.5 text-gray-600 group-hover:text-gray-400 shrink-0" />
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
