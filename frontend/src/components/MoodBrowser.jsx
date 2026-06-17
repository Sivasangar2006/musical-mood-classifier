/**
 * MoodBrowser
 * "What's your mood today?" — pick a mood, get an instant Deezer playlist.
 * No upload needed. Lives below the main upload/result section.
 */

import { useState } from 'react';
import DeezerRecommendations from './DeezerRecommendations.jsx';

const MOODS = [
  { name: 'Happy',     emoji: '😊', grad: 'from-yellow-500 to-orange-400',   ring: 'ring-yellow-500'  },
  { name: 'Energetic', emoji: '⚡', grad: 'from-red-500 to-pink-500',        ring: 'ring-red-500'     },
  { name: 'Angry',     emoji: '😠', grad: 'from-purple-600 to-red-600',      ring: 'ring-purple-500'  },
  { name: 'Sad',       emoji: '😢', grad: 'from-blue-500 to-indigo-500',     ring: 'ring-blue-500'    },
  { name: 'Relaxed',   emoji: '😌', grad: 'from-emerald-500 to-teal-500',    ring: 'ring-emerald-500' },
];

export default function MoodBrowser() {
  const [selected, setSelected] = useState(null);

  return (
    <section className="max-w-2xl mx-auto px-4 py-12">
      {/* Title */}
      <div className="text-center mb-8">
        <h2 className="text-2xl md:text-3xl font-display font-bold text-white">
          What's your mood today?
        </h2>
        <p className="text-gray-500 text-sm mt-2">
          Pick a mood and get an instant playlist — no upload needed
        </p>
      </div>

      {/* Mood cards */}
      <div className="flex flex-wrap justify-center gap-3 mb-8">
        {MOODS.map(m => (
          <button
            key={m.name}
            onClick={() => setSelected(selected === m.name ? null : m.name)}
            className={`
              flex items-center gap-2 px-5 py-2.5 rounded-full font-medium text-sm
              transition-all duration-200 border-2
              ${selected === m.name
                ? `bg-gradient-to-r ${m.grad} text-white border-transparent shadow-lg scale-105`
                : 'bg-gray-900 text-gray-300 border-gray-700 hover:border-gray-500 hover:text-white'}
            `}
          >
            <span className="text-base">{m.emoji}</span>
            {m.name}
          </button>
        ))}
      </div>

      {/* Playlist */}
      {selected && (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
          <DeezerRecommendations mood={selected} />
        </div>
      )}
    </section>
  );
}
