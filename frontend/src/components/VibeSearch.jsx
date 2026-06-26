/**
 * VibeSearch — describe a feeling or scene in plain words and get songs that
 * sound like it. No tags, no keyword matching.
 */

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Loader2, ArrowRight } from 'lucide-react';
import { searchByVibe } from '../api/client.js';
import { revealUp } from '../lib/motion.js';
import CorpusTracks from './CorpusTracks.jsx';
import SectionHeading from './SectionHeading.jsx';

const SUGGESTIONS = [
  'rainy sunday morning coffee',
  'late night city drive',
  'workout rage',
  'heartbreak at 2am',
  'sunny road trip',
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
      if (!data.tracks.length) setError('No matches found — try describing it differently.');
    } catch {
      setError('Search is unavailable right now. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.section
      variants={revealUp} initial="hidden" whileInView="show" viewport={{ once: true, margin: '-80px' }}
      className="max-w-2xl mx-auto px-4 sm:px-6 py-14"
    >
      <SectionHeading index="01" title="Search by feeling" subtitle="Describe a moment or mood — get songs that sound like it." />

      <form onSubmit={(e) => { e.preventDefault(); run(query); }} className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. rainy sunday morning coffee"
          className="flex-1 px-4 h-12 bg-card border border-line-strong rounded-xl2 text-ink
                     placeholder-ink-faint shadow-card focus:outline-none focus:border-clay focus:ring-2 focus:ring-clay/20 transition-shadow"
        />
        <button type="submit" disabled={loading}
          className="px-5 h-12 rounded-xl2 bg-clay hover:bg-clay-dark text-white font-semibold transition-colors
                     disabled:opacity-50 flex items-center gap-2 cursor-pointer shrink-0">
          {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <>Find <ArrowRight className="w-4 h-4" strokeWidth={2.25} /></>}
        </button>
      </form>

      <div className="flex flex-wrap gap-2 mt-3">
        {SUGGESTIONS.map((s) => (
          <button key={s} onClick={() => { setQuery(s); run(s); }}
            className="text-xs px-3 py-1.5 rounded-full bg-card border border-line text-ink-soft
                       hover:border-clay hover:text-clay transition-colors cursor-pointer">
            {s}
          </button>
        ))}
      </div>

      {error && <p className="text-energetic text-sm mt-4">{error}</p>}

      {tracks.length > 0 && (
        <div className="mt-6 card p-5">
          <CorpusTracks
            tracks={tracks}
            heading={`Songs that feel like “${active}”`}
            subheading="Ranked by how closely they match · 30-second previews"
            accent="#C2553A"
          />
        </div>
      )}
    </motion.section>
  );
}
