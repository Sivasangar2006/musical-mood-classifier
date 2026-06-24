/**
 * MoodBrowser
 * "What's your mood today?" — pick a mood, get songs the MODEL placed nearest
 * that mood in valence/arousal space (not a keyword search). No upload needed.
 */

import { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import { getVARecommendations } from '../api/client.js';
import CorpusTracks from './CorpusTracks.jsx';

const MOODS = [
  { name: 'Happy',     emoji: '😊', grad: 'from-yellow-500 to-orange-400', glow: '#d97706' },
  { name: 'Energetic', emoji: '⚡', grad: 'from-red-500 to-pink-500',      glow: '#ef4444' },
  { name: 'Angry',     emoji: '😠', grad: 'from-purple-600 to-red-600',    glow: '#7c3aed' },
  { name: 'Sad',       emoji: '😢', grad: 'from-blue-500 to-indigo-500',   glow: '#3b82f6' },
  { name: 'Relaxed',   emoji: '😌', grad: 'from-emerald-500 to-teal-500',  glow: '#10b981' },
];

export default function MoodBrowser() {
  const [selected, setSelected] = useState(null);
  const [tracks, setTracks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!selected) { setTracks([]); return; }
    let active = true;
    setLoading(true); setError(null);
    getVARecommendations(selected.name, 12)
      .then((d) => { if (active) setTracks(d.tracks); })
      .catch(() => { if (active) setError('Could not load recommendations. Is the backend running?'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [selected]);

  return (
    <section className="max-w-2xl mx-auto px-4 py-12">
      <div className="text-center mb-8">
        <h2 className="text-2xl md:text-3xl font-display font-bold text-white">
          What's your mood today?
        </h2>
        <p className="text-gray-500 text-sm mt-2">
          Pick a mood — songs the model placed nearest it in emotion space
        </p>
      </div>

      <div className="flex flex-wrap justify-center gap-3 mb-8">
        {MOODS.map((m) => (
          <button
            key={m.name}
            onClick={() => setSelected(selected?.name === m.name ? null : m)}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-full font-medium text-sm transition-all duration-200 border-2
              ${selected?.name === m.name
                ? `bg-gradient-to-r ${m.grad} text-white border-transparent shadow-lg scale-105`
                : 'bg-gray-900 text-gray-300 border-gray-700 hover:border-gray-500 hover:text-white'}`}
          >
            <span className="text-base">{m.emoji}</span>
            {m.name}
          </button>
        ))}
      </div>

      {selected && (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
          {loading ? (
            <div className="flex items-center gap-2 text-gray-500 text-sm py-6 justify-center">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Finding {selected.name.toLowerCase()} tracks…</span>
            </div>
          ) : error ? (
            <p className="text-red-400 text-sm text-center py-4">{error}</p>
          ) : (
            <CorpusTracks
              tracks={tracks}
              heading={`${selected.name} songs`}
              subheading="Nearest the mood in valence/arousal space · 30s previews"
              accent={selected.glow}
            />
          )}
        </div>
      )}
    </section>
  );
}
