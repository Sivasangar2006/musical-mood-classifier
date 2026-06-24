/**
 * ValenceArousalPlot
 * Russell's circumplex: plots the song as a point in the 2-D emotion plane.
 * X = valence (unpleasant -> pleasant), Y = arousal (calm -> excited).
 * The faint dots are the recommended songs — showing visually that recs come
 * from nearby in emotion space, not from a label lookup.
 */

const SIZE = 280;
const C = SIZE / 2;          // centre
const R = 120;               // [-1,1] maps to +-R pixels around centre

// normalised [-1,1] -> svg coords (y is inverted: +arousal is up)
const px = (v) => C + v * R;
const py = (a) => C - a * R;

const QUADRANTS = [
  { x: C + R * 0.55, y: C - R * 0.78, label: 'Excited',  sub: 'happy' },
  { x: C - R * 0.55, y: C - R * 0.78, label: 'Tense',    sub: 'angry' },
  { x: C - R * 0.55, y: C + R * 0.82, label: 'Sad',      sub: 'depressed' },
  { x: C + R * 0.55, y: C + R * 0.82, label: 'Calm',     sub: 'relaxed' },
];

export default function ValenceArousalPlot({ valence, arousal, mood, color = '#7c3aed', similar = [] }) {
  return (
    <div className="flex flex-col items-center">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="w-full max-w-[280px]">
        {/* outer circle */}
        <circle cx={C} cy={C} r={R} fill="rgba(255,255,255,0.02)" stroke="#374151" strokeWidth="1" />
        <circle cx={C} cy={C} r={R * 0.5} fill="none" stroke="#1f2937" strokeWidth="1" strokeDasharray="3 3" />

        {/* axes */}
        <line x1={C - R} y1={C} x2={C + R} y2={C} stroke="#374151" strokeWidth="1" />
        <line x1={C} y1={C - R} x2={C} y2={C + R} stroke="#374151" strokeWidth="1" />

        {/* axis labels */}
        <text x={C + R + 4} y={C + 3} fontSize="9" fill="#6b7280" textAnchor="start">+valence</text>
        <text x={C - R - 4} y={C + 3} fontSize="9" fill="#6b7280" textAnchor="end">−</text>
        <text x={C} y={C - R - 5} fontSize="9" fill="#6b7280" textAnchor="middle">+arousal</text>
        <text x={C} y={C + R + 13} fontSize="9" fill="#6b7280" textAnchor="middle">−</text>

        {/* quadrant labels */}
        {QUADRANTS.map((q) => (
          <text key={q.label} x={q.x} y={q.y} textAnchor="middle" fill="#4b5563" fontSize="11" fontWeight="600">
            {q.label}
          </text>
        ))}

        {/* recommended songs as faint neighbourhood dots */}
        {similar.map((s, i) =>
          (typeof s.valence === 'number' && typeof s.arousal === 'number') ? (
            <circle key={i} cx={px(s.valence)} cy={py(s.arousal)} r="3"
              fill={color} opacity="0.28" />
          ) : null
        )}

        {/* the song's point */}
        <circle cx={px(valence)} cy={py(arousal)} r="11" fill={color} opacity="0.25">
          <animate attributeName="r" values="9;15;9" dur="2.5s" repeatCount="indefinite" />
        </circle>
        <circle cx={px(valence)} cy={py(arousal)} r="6" fill={color} stroke="#fff" strokeWidth="2" />
      </svg>

      <p className="text-gray-500 text-xs mt-1">
        <span className="text-gray-300 font-medium">{mood}</span>
        {' · '}valence {valence >= 0 ? '+' : ''}{valence.toFixed(2)} · arousal {arousal >= 0 ? '+' : ''}{arousal.toFixed(2)}
      </p>
    </div>
  );
}
