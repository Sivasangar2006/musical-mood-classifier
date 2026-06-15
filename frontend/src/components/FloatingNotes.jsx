import { useMemo } from 'react';

const NOTES = ['♪', '♫', '♬', '🎵', '🎶', '♩'];

export default function FloatingNotes() {
  const particles = useMemo(() =>
    Array.from({ length: 700 }, (_, i) => ({
      id: i,
      note: NOTES[i % NOTES.length],
      left: `${Math.random() * 100}%`,
      top: `${Math.random() * 100}%`,
      size: 10 + Math.random() * 18,
      opacity: 0.06 + Math.random() * 0.04,
      anim: ['animate-float-1', 'animate-float-2', 'animate-float-3'][i % 3],
      delay: `${Math.random() * 5}s`,
    })), []);

  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0" aria-hidden="true">
      {/* Gradient orbs */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-violet-600/10 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 -right-32 w-80 h-80 bg-blue-600/8 rounded-full blur-3xl" />
      <div className="absolute top-3/4 left-1/3 w-64 h-64 bg-emerald-600/6 rounded-full blur-3xl" />

      {/* Floating notes */}
      {particles.map(p => (
        <span
          key={p.id}
          className={`absolute select-none ${p.anim}`}
          style={{
            left: p.left, top: p.top,
            fontSize: p.size, opacity: p.opacity,
            animationDelay: p.delay,
          }}
        >
          {p.note}
        </span>
      ))}
    </div>
  );
}
