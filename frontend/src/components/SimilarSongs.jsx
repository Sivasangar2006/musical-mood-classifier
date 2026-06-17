/**
 * SimilarSongs
 * Shows the top-k acoustically similar songs found by FAISS similarity search
 * on the 512-dim ResNet18 embeddings.
 */

const MOOD_COLOR = {
  Happy:     'text-yellow-400',
  Energetic: 'text-red-400',
  Angry:     'text-purple-400',
  Sad:       'text-blue-400',
  Relaxed:   'text-emerald-400',
};

const MOOD_EMOJI = {
  Happy: '😊', Energetic: '⚡', Angry: '😠', Sad: '😢', Relaxed: '😌',
};

export default function SimilarSongs({ songs = [] }) {
  if (!songs.length) return null;

  return (
    <div className="mt-8">
      <p className="text-gray-500 text-xs uppercase tracking-widest font-semibold mb-4">
        Acoustically Similar
      </p>
      <p className="text-gray-600 text-xs mb-3">
        Found by FAISS cosine search on 512-dim CNN embeddings
      </p>
      <div className="space-y-2">
        {songs.map((song, i) => (
          <div
            key={i}
            className="flex items-center gap-3 bg-gray-800/50 rounded-xl px-4 py-2.5
                       hover:bg-gray-800 transition-colors"
          >
            {/* Rank */}
            <span className="text-gray-600 font-mono text-xs w-4 shrink-0">{i + 1}</span>

            {/* Mood emoji */}
            <span className="text-base shrink-0">{MOOD_EMOJI[song.mood] ?? '🎵'}</span>

            {/* Filename + mood */}
            <div className="flex-1 min-w-0">
              <p className="text-white text-sm font-medium truncate">
                {song.filename.replace(/\.\w+$/, '').replace(/[._-]/g, ' ')}
              </p>
              <p className={`text-xs ${MOOD_COLOR[song.mood] ?? 'text-gray-400'}`}>
                {song.mood}
              </p>
            </div>

            {/* Cosine similarity score */}
            <span className="text-gray-500 font-mono text-xs shrink-0">
              {(song.score * 100).toFixed(0)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
