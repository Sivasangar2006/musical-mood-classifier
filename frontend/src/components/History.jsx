import { useState, useEffect } from 'react';
import { getHistory } from '../api/client.js';

const EMOJIS = { Happy:'😊', Energetic:'⚡', Angry:'😠', Sad:'😢', Relaxed:'😌' };
const GRADIENTS = {
  Happy:'from-yellow-500/20 to-orange-500/5',
  Energetic:'from-red-500/20 to-pink-500/5',
  Angry:'from-purple-500/20 to-red-500/5',
  Sad:'from-blue-500/20 to-indigo-500/5',
  Relaxed:'from-green-500/20 to-emerald-500/5',
};

export default function History() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await getHistory(15);
        setHistory(data.predictions);
      } catch { setError('Could not load history'); }
      finally { setLoading(false); }
    })();
  }, []);

  if (loading) {
    return (
      <div className="text-center py-16">
        <div className="flex items-center justify-center gap-2 text-3xl">
          {['♩','♪','♫','♬'].map((n,i) => (
            <span key={i} className={`animate-note-${i+1} text-violet-400`}>{n}</span>
          ))}
        </div>
        <p className="text-gray-500 mt-4">Loading history…</p>
      </div>
    );
  }
  if (error) return <p className="text-center text-red-400 py-12">{error}</p>;
  if (!history.length) {
    return (
      <div className="text-center py-16 glass max-w-md mx-auto">
        <div className="text-5xl mb-3">🎵</div>
        <p className="text-gray-400 text-lg font-medium">No predictions yet</p>
        <p className="text-gray-600 text-sm mt-1">Upload your first song to get started!</p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      <h3 className="text-gray-500 text-xs uppercase tracking-widest font-semibold mb-5">
        Recent Predictions
      </h3>
      <div className="space-y-2.5">
        {history.map((p, idx) => (
          <div
            key={p.id}
            className="flex items-center justify-between p-4 glass hover:bg-white/[0.06]
                       transition-all duration-200 group"
          >
            <div className="flex items-center gap-3.5 min-w-0">
              <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${GRADIENTS[p.mood] || 'from-gray-700 to-gray-800'}
                              flex items-center justify-center text-xl shrink-0`}>
                {EMOJIS[p.mood] || '🎵'}
              </div>
              <div className="min-w-0">
                <p className="text-white font-medium text-sm truncate max-w-[200px]">{p.filename}</p>
                <p className="text-gray-600 text-xs">{new Date(p.created_at).toLocaleDateString()}</p>
              </div>
            </div>
            <div className="text-right shrink-0 ml-3">
              <p className="text-white font-semibold text-sm">{p.mood}</p>
              <p className="text-gray-600 text-xs font-mono">{(p.confidence*100).toFixed(0)}%</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}