/**
 * HistoryPanel — slide-over showing the signed-in user's analysed songs with
 * their mood + confidence. If signed out, prompts to sign in.
 */

import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X, Clock } from 'lucide-react';
import { getVAHistory } from '../api/client.js';
import { useAuth } from '../auth/AuthContext.jsx';
import { ease } from '../lib/motion.js';

const MOOD_COLOR = {
  Happy: '#C98A12', Energetic: '#D6294B', Angry: '#7E3CC0', Sad: '#2563EB', Relaxed: '#0E8C63',
};

export default function HistoryPanel({ open, onClose }) {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open || !user) return;
    setLoading(true); setError(null);
    getVAHistory(50)
      .then((d) => setItems(d.analyses))
      .catch(() => setError('Could not load your history. Please try again.'))
      .finally(() => setLoading(false));
  }, [open, user]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[60] flex justify-end">
          <motion.div
            className="absolute inset-0 bg-black/40"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            className="relative w-full max-w-md h-full bg-paper border-l border-line overflow-y-auto"
            initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
            transition={{ duration: 0.32, ease }}
          >
            <div className="sticky top-0 bg-paper border-b border-line px-5 py-4 flex items-center justify-between">
              <h2 className="font-display text-lg font-bold text-ink flex items-center gap-2">
                <Clock className="w-5 h-5 text-clay" strokeWidth={2} /> Your history
              </h2>
              <button onClick={onClose}
                className="w-8 h-8 rounded-lg border border-line text-ink-soft hover:text-ink hover:border-line-strong
                           flex items-center justify-center cursor-pointer transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5">
              {!user ? (
                <div className="text-center py-20 px-4">
                  <div className="w-14 h-14 rounded-xl2 bg-clay-wash flex items-center justify-center mx-auto mb-4">
                    <Clock className="w-7 h-7 text-clay" strokeWidth={2} />
                  </div>
                  <p className="text-ink font-semibold mb-1.5">Sign in to view your history</p>
                  <p className="text-ink-soft text-sm">
                    Every song you analyse is saved to your account with its mood and confidence.
                    Use the sign-in button at the top right.
                  </p>
                </div>
              ) : loading ? (
                <p className="text-ink-soft text-center py-12">Loading…</p>
              ) : error ? (
                <p className="text-energetic text-center py-12">{error}</p>
              ) : items.length === 0 ? (
                <p className="text-ink-soft text-center py-20">No songs yet — search one to get started.</p>
              ) : (
                <div className="space-y-2">
                  {items.map((a, i) => (
                    <motion.div
                      key={a.id}
                      initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.03, duration: 0.3 }}
                      className="bg-card border border-line rounded-xl p-3 flex items-center gap-3"
                    >
                      <div className="w-1 h-10 rounded-full shrink-0" style={{ background: MOOD_COLOR[a.mood] || '#999' }} />
                      <div className="flex-1 min-w-0">
                        <p className="text-ink text-sm font-medium truncate">{a.title || 'Uploaded clip'}</p>
                        <p className="text-ink-soft text-xs truncate">{a.artist || a.quadrant}</p>
                      </div>
                      <div className="text-right shrink-0">
                        <p className="text-sm font-semibold" style={{ color: MOOD_COLOR[a.mood] || '#1A1A1A' }}>{a.mood}</p>
                        <p className="text-ink-faint text-xs">{Math.round(a.confidence * 100)}%</p>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
