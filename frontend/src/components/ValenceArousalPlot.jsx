/**
 * ValenceArousalPlot — plots the song as a point in the 2-D emotion plane.
 * X = valence (unpleasant → pleasant), Y = arousal (calm → excited).
 * Faint dots are the recommended songs, showing recs come from nearby in
 * emotion space. The song's point animates in from the centre.
 */

import { motion } from 'framer-motion';

const SIZE = 280;
const C = SIZE / 2;
const R = 116;

const px = (v) => C + v * R;
const py = (a) => C - a * R;

const QUADRANTS = [
  { x: C + R * 0.52, y: C - R * 0.82, label: 'Excited' },
  { x: C - R * 0.52, y: C - R * 0.82, label: 'Tense' },
  { x: C - R * 0.52, y: C + R * 0.86, label: 'Low' },
  { x: C + R * 0.52, y: C + R * 0.86, label: 'Calm' },
];

export default function ValenceArousalPlot({ valence, arousal, mood, color = '#C2553A', similar = [] }) {
  return (
    <div className="flex flex-col items-center">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="w-full max-w-[280px]">
        <circle cx={C} cy={C} r={R} fill="rgb(var(--paper))" stroke="rgb(var(--line-strong))" strokeWidth="1.5" />
        <circle cx={C} cy={C} r={R * 0.5} fill="none" stroke="rgb(var(--line))" strokeWidth="1" strokeDasharray="3 4" />
        <line x1={C - R} y1={C} x2={C + R} y2={C} stroke="rgb(var(--line))" strokeWidth="1" />
        <line x1={C} y1={C - R} x2={C} y2={C + R} stroke="rgb(var(--line))" strokeWidth="1" />

        <text x={C + R + 2} y={C + 3} fontSize="9" fill="rgb(var(--ink-faint))" textAnchor="end">pleasant</text>
        <text x={C - R + 2} y={C + 3} fontSize="9" fill="rgb(var(--ink-faint))" textAnchor="start">unpleasant</text>
        <text x={C} y={C - R - 5} fontSize="9" fill="rgb(var(--ink-faint))" textAnchor="middle">energetic</text>
        <text x={C} y={C + R + 13} fontSize="9" fill="rgb(var(--ink-faint))" textAnchor="middle">calm</text>

        {QUADRANTS.map((q) => (
          <text key={q.label} x={q.x} y={q.y} textAnchor="middle" fill="rgb(var(--ink-faint))" fontSize="11" fontWeight="600">
            {q.label}
          </text>
        ))}

        {similar.map((s, i) =>
          (typeof s.valence === 'number' && typeof s.arousal === 'number') ? (
            <motion.circle
              key={i}
              cx={px(s.valence)} cy={py(s.arousal)} r="3.5" fill={color}
              initial={{ opacity: 0 }} animate={{ opacity: 0.3 }}
              transition={{ delay: 0.5 + i * 0.04, duration: 0.4 }}
            />
          ) : null
        )}

        {/* The song's point — animates out from the centre. */}
        <motion.circle
          cx={C} cy={C} r="7" fill={color} stroke="#fff" strokeWidth="2.5"
          animate={{ cx: px(valence), cy: py(arousal) }}
          transition={{ type: 'spring', stiffness: 120, damping: 16, delay: 0.15 }}
        />
        <motion.circle
          cx={C} cy={C} r="7" fill={color} opacity="0.25"
          animate={{ cx: px(valence), cy: py(arousal), r: [7, 16, 7] }}
          transition={{
            cx: { type: 'spring', stiffness: 120, damping: 16, delay: 0.15 },
            cy: { type: 'spring', stiffness: 120, damping: 16, delay: 0.15 },
            r: { duration: 2.4, repeat: Infinity, ease: 'easeInOut', delay: 0.8 },
          }}
        />
      </svg>

      <p className="text-ink-soft text-xs mt-1">
        <span className="text-ink font-semibold">{mood}</span>
        {' · '}valence {valence >= 0 ? '+' : ''}{valence.toFixed(2)} · arousal {arousal >= 0 ? '+' : ''}{arousal.toFixed(2)}
      </p>
    </div>
  );
}
