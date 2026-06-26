/**
 * Shared framer-motion variants and easings.
 * Kept small and reused everywhere so motion feels consistent — high-signal
 * transitions that clarify state, not decoration.
 */

export const ease = [0.22, 1, 0.36, 1]; // gentle, slightly springy ease-out

// Section reveal on scroll into view.
export const revealUp = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease } },
};

// Stagger a list of children in.
export const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.05, delayChildren: 0.04 } },
};

export const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35, ease } },
};

// Dropdown / popover enter-exit.
export const popover = {
  hidden: { opacity: 0, y: -6, scale: 0.985 },
  show: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.18, ease } },
  exit: { opacity: 0, y: -6, scale: 0.985, transition: { duration: 0.12, ease } },
};

// Result card entrance.
export const cardIn = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.55, ease } },
};
