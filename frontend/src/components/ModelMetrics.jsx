/**
 * ModelMetrics — "About the model" dashboard.
 * Surfaces the honest evaluation numbers (R², MAE, quadrant accuracy, calibration)
 * so the project shows its work. Fetched from GET /va/metrics.
 */

import { useEffect, useState } from 'react';
import { getMetrics } from '../api/client.js';

function Stat({ label, value, sub }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center">
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-gray-400 text-xs mt-1">{label}</p>
      {sub && <p className="text-gray-600 text-[10px] mt-0.5">{sub}</p>}
    </div>
  );
}

export default function ModelMetrics() {
  const [m, setM] = useState(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    getMetrics().then(setM).catch(() => setM(null));
  }, []);

  if (!m) return null;
  const v = m.axes.valence, a = m.axes.arousal;

  return (
    <section className="max-w-3xl mx-auto px-4 py-12">
      <div className="text-center mb-6">
        <h2 className="text-2xl md:text-3xl font-display font-bold text-white">How good is the model?</h2>
        <p className="text-gray-500 text-sm mt-2">
          Held-out evaluation on {m.n_test} DEAM clips · {m.embedding} · {m.head}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-6">
        <Stat label="Valence R²" value={v.r2} sub="hard axis in MIR" />
        <Stat label="Arousal R²" value={a.r2} sub="energy axis" />
        <Stat label="Quadrant accuracy" value={`${Math.round(m.quadrant_accuracy * 100)}%`} sub="vs 25% chance" />
      </div>

      <button onClick={() => setShown(!shown)}
        className="mx-auto block text-gray-500 hover:text-gray-300 text-xs transition-colors">
        {shown ? 'Hide details ▲' : 'Show full metrics ▼'}
      </button>

      {shown && (
        <div className="mt-4 bg-gray-900 border border-gray-800 rounded-xl p-5 text-sm">
          <table className="w-full text-left">
            <thead>
              <tr className="text-gray-500 text-xs">
                <th className="pb-2">axis</th><th className="pb-2">R²</th>
                <th className="pb-2">MAE (1–9)</th><th className="pb-2">variance kept</th>
                <th className="pb-2">baseline R²</th>
              </tr>
            </thead>
            <tbody className="text-gray-300">
              {['valence', 'arousal'].map((ax) => (
                <tr key={ax} className="border-t border-gray-800">
                  <td className="py-2 capitalize">{ax}</td>
                  <td>{m.axes[ax].r2}</td>
                  <td>{m.axes[ax].mae_1to9}</td>
                  <td>{Math.round(m.axes[ax].variance_ratio * 100)}%</td>
                  <td className="text-gray-600">{m.axes[ax].baseline_r2}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-gray-600 text-xs mt-4 leading-relaxed">
            Valence (pleasant↔unpleasant) is notoriously the harder axis in music-emotion research;
            a linear probe on frozen CLAP embeddings beating R²≈0.5 is competitive with deep models.
            "Variance kept" shows mild regression-to-the-mean. Baseline R²≈0 confirms the model is
            genuinely learning, not predicting the average.
          </p>
        </div>
      )}
    </section>
  );
}
