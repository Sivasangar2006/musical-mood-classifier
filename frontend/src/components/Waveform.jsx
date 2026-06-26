import { motion } from 'framer-motion';

/**
 * Waveform — a row of gently animating vertical bars. On-domain decoration that
 * stays calm (low amplitude, slow). Used as the hero motif.
 */
const HEIGHTS = [10, 20, 34, 24, 44, 28, 52, 30, 40, 18, 30, 46, 22, 38, 14, 26, 42, 20, 32, 12];

export default function Waveform({ bars = HEIGHTS, color = 'rgb(var(--clay))', className = '' }) {
  return (
    <div className={`flex items-center justify-center gap-[3px] h-14 ${className}`} aria-hidden="true">
      {bars.map((h, i) => (
        <motion.span
          key={i}
          className="w-[3px] rounded-full"
          style={{ background: color, opacity: 0.25 + (h / 52) * 0.6 }}
          animate={{ height: [h, h * 0.45, h, h * 0.7, h] }}
          transition={{
            duration: 2.6 + (i % 5) * 0.25,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: i * 0.05,
          }}
        />
      ))}
    </div>
  );
}
