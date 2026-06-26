/**
 * MoodBrowser — pick a mood, get songs the model placed nearest it in emotion
 * space (not a keyword search). No upload needed.
 */

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import { getVARecommendations } from '../api/client.js';
import { revealUp } from '../lib/motion.js';
import CorpusTracks from './CorpusTracks.jsx';
import SectionHeading from './SectionHeading.jsx';

const MOODS = [
  { name: 'Happy',     color: '#C98A12' },
  { name: 'Energetic', color: '#D6294B' },
  { name: 'Angry',     color: '#7E3CC0' },
  { name: 'Sad',       color: '#2563EB' },
  { name: 'Relaxed',   color: '#0E8C63' },
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
      .catch(() => { if (active) setError('Could not load recommendations. Please try again.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [selected]);

  return (
    <motion.section
      variants={revealUp} initial="hidden" whileInView="show" viewport={{ once: true, margin: '-80px' }}
      className="max-w-2xl mx-auto px-4 sm:px-6 py-14"
    >
      <SectionHeading index="02" title="Browse by mood" subtitle="Pick a feeling and hear what fits." />

      <div className="flex flex-wrap gap-2 mb-6">
        {MOODS.map((m) => {
          const on = selected?.name === m.name;
          return (
            <motion.button
              key={m.name}
              onClick={() => setSelected(on ? null : m)}
              whileTap={{ scale: 0.96 }}
              className={`flex items-center gap-2 px-4 py-2 rounded-full font-medium text-sm border transition-colors cursor-pointer
                          ${on ? '' : 'bg-card border-line text-ink hover:border-line-strong'}`}
              style={on ? { background: m.color, borderColor: m.color, color: '#fff' } : undefined}
            >
              {!on && <span className="w-2 h-2 rounded-full" style={{ background: m.color }} />}
              {m.name}
            </motion.button>
          );
        })}
      </div>

      <AnimatePresence mode="wait">
        {selected && (
          <motion.div
            key={selected.name}
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25 }}
            className="card p-5"
          >
            {loading ? (
              <div className="flex items-center gap-2 text-ink-soft text-sm py-6 justify-center">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Finding {selected.name.toLowerCase()} songs…</span>
              </div>
            ) : error ? (
              <p className="text-energetic text-sm text-center py-4">{error}</p>
            ) : (
              <CorpusTracks
                tracks={tracks}
                heading={`${selected.name} songs`}
                subheading="Closest to this mood in emotion space · 30-second previews"
                accent={selected.color}
              />
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.section>
  );
}
