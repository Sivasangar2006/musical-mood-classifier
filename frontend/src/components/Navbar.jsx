import { Music } from 'lucide-react';

export default function Navbar({ onReset }) {
  return (
    <header className="sticky top-0 z-50 bg-gray-950 border-b border-gray-800">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
        <button onClick={onReset} className="flex items-center gap-2.5 hover:opacity-80 transition-opacity">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-600 to-fuchsia-600 flex items-center justify-center">
            <Music className="w-5 h-5 text-white" />
          </div>
          <span className="text-white font-display font-bold text-xl tracking-tight">
            Mood<span className="text-violet-400">Wave</span>
          </span>
        </button>
      </div>
    </header>
  );
}
