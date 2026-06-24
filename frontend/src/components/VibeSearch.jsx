/**
 * VibeSearch
 * Cross-modal text-to-mood discovery: describe a feeling/scene in plain words and
 * get songs that *sound* like it — powered by CLAP's shared audio/text embedding
 * space. No tags, no keyword matching.
 */

import { useState } from 'react';
import { Sparkles, Loader2 } from 'lucide-react';
import { searchByVibe } from '../api/client.js';
import CorpusTracks from './CorpusTracks.jsx';

const SUGGESTIONS = [
  'rainy sunday morning coffee',
  'late night drive in the city',
  'angry workout rage',
  'heartbreak crying at 2am',
  'sunny road trip with friends',
];

export default function VibeSearch() {
  const [query, setQuery] = useState('');
  const [tracks, setTracks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [active, setActive] = useState('');

  const run = async (q) => {
    if (!q.trim()) return;
    setLoading(true); setError(null); setActive(q);
    try {
      const data = await searchByVibe(q.trim(), 12);
      setTracks(data.tracks);
      if (!data.tracks.length) setError('No matches found.');
    } catch {
      setError('Search failed. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="max-w-2xl mx-auto px-4 py-12">
      <div className="text-center mb-6">
        <h2 className="text-2xl md:text-3xl font-display font-bold text-white">
          Describe a vibe
        </h2>
        <p className="text-gray-500 text-sm mt-2">
          Type a feeling or scene — get songs that <em>sound</em> like it (cross-modal CLAP search)
        </p>
      </div>

      <form onSubmit={(e) => { e.preventDefault(); run(query); }} className="flex gap-2">
        <div className="flex-1 relative">
          <Sparkles className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-violet-500" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. rainy sunday morning coffee"
            className="w-full pl-10 pr-3 py-3.5 bg-gray-900 border border-gray-700 rounded-xl
                       text-white placeholder-gray-600 focus:outline-none focus:border-violet-500 transition-colors"
          />
        </div>
        <button type="submit" disabled={loading}
          className="px-5 py-3.5 rounded-xl bg-violet-600 hover:bg-violet-500 text-white font-semibold transition-colors disabled:opacity-50">
          {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Find'}
        </button>
      </form>

      {/* Suggestion chips */}
      <div className="flex flex-wrap justify-center gap-2 mt-4">
        {SUGGESTIONS.map((s) => (
          <button key={s} onClick={() => { setQuery(s); run(s); }}
            className="text-xs px-3 py-1.5 rounded-full bg-gray-900 border border-gray-700
                       text-gray-400 hover:border-violet-600 hover:text-violet-300 transition-colors">
            {s}
          </button>
        ))}
      </div>

      {error && <p className="text-red-400 text-sm text-center mt-4">{error}</p>}

      {tracks.length > 0 && (
        <div className="mt-6 bg-gray-900 border border-gray-800 rounded-2xl p-6">
          <CorpusTracks
            tracks={tracks}
            heading={`Songs that feel like "${active}"`}
            subheading="Ranked by CLAP audio↔text similarity · 30s previews"
            accent="#8b5cf6"
          />
        </div>
      )}
    </section>
  );
}
