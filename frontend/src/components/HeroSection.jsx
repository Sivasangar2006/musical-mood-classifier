import { motion } from 'framer-motion';
import { ease } from '../lib/motion.js';
import Waveform from './Waveform.jsx';

export default function HeroSection() {
  return (
    <section className="dot-grid pt-14 pb-6 text-center">
      <motion.span
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease }}
        className="inline-flex items-center gap-2 text-xs font-semibold tracking-wide uppercase
                   text-clay bg-clay-wash border border-clay/20 rounded-full px-3 py-1"
      >
        <span className="w-1.5 h-1.5 rounded-full bg-clay" />
        Music, by feeling
      </motion.span>

      <motion.h1
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease, delay: 0.05 }}
        className="font-display text-4xl md:text-[3.25rem] font-bold text-ink leading-[1.08] tracking-tight mt-4"
      >
        Hear the feeling
        <br className="hidden sm:block" />
        <span className="text-clay"> in any song</span>
      </motion.h1>

      <motion.p
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease, delay: 0.12 }}
        className="mt-4 text-ink-soft text-base md:text-lg max-w-md mx-auto leading-relaxed"
      >
        Search a track to read its mood — then hear songs that feel the same.
      </motion.p>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.25 }}
        className="mt-6 max-w-sm mx-auto"
      >
        <Waveform />
      </motion.div>
    </section>
  );
}
