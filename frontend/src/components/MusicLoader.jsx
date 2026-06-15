export default function MusicLoader({ text = 'Analyzing mood...' }) {
  const notes = ['♩', '♪', '♫', '♬'];
  return (
    <div className="flex flex-col items-center gap-5 py-10">
      {/* Bouncing music notes */}
      <div className="flex items-end gap-3">
        {notes.map((n, i) => (
          <span
            key={i}
            className={`text-3xl animate-note-${i + 1} text-violet-400`}
          >
            {n}
          </span>
        ))}
      </div>

      {/* Equalizer bars */}
      <div className="flex items-end gap-1 h-10">
        {[1,2,3,4,5,4,3].map((_, i) => (
          <div
            key={i}
            className={`eq-bar bg-gradient-to-t from-violet-600 to-fuchsia-400 animate-eq-${(i % 5) + 1}`}
            style={{ height: '40%', width: 4 }}
          />
        ))}
      </div>

      <p className="text-gray-400 text-sm font-medium tracking-wide">{text}</p>
    </div>
  );
}
