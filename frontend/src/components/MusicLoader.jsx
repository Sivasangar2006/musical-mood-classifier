import { motion } from 'framer-motion';

const BARS = [0, 1, 2, 3, 4, 5, 6];

export default function MusicLoader({ text = 'Listening…' }) {
  return (
    <div className="flex flex-col items-center gap-5 py-6">
      <div className="flex items-end gap-1.5 h-12">
        {BARS.map((i) => (
          <motion.span
            key={i}
            className="w-1.5 rounded-full bg-clay"
            initial={{ height: 8 }}
            animate={{ height: [8, 40, 14, 30, 8] }}
            transition={{
              duration: 1.1,
              repeat: Infinity,
              ease: 'easeInOut',
              delay: i * 0.09,
            }}
          />
        ))}
      </div>
      <p className="text-ink-soft text-sm font-medium">{text}</p>
    </div>
  );
}
