import { Play, Pause } from 'lucide-react';

/**
 * props:
 *   isPlaying   bool
 *   onToggle    () => void
 *   labelBg     inline-style background string for the center label (optional)
 *   glowColor   CSS color used for the spinning glow ring (optional)
 *   emoji       string — shown on the center label instead of text (optional)
 *   topText     string — small top text on the label (optional)
 *   bottomText  string — small bottom text on the label (optional)
 */
export default function VinylDisc({
  isPlaying,
  onToggle,
  labelBg = 'radial-gradient(circle, #5b21b6, #3b0764)',
  glowColor = '#7c3aed',
  emoji,
  topText = 'MoodWave',
  bottomText = '',
  showLabel = true,
}) {
  const hex = glowColor;

  return (
    <div className="relative w-52 h-52 mx-auto select-none cursor-pointer" onClick={onToggle}>
      {/* Spinning disc */}
      <div
        className={`w-full h-full rounded-full transition-shadow duration-500 ${
          isPlaying ? 'animate-spin-slow' : ''
        }`}
        style={{
          background: `radial-gradient(circle at center,
            transparent 0%, transparent 22%,
            #0d0d0d 23%, #1a1a1a 26%, #0d0d0d 30%, #181818 33%,
            #0d0d0d 38%, #1a1a1a 41%, #0d0d0d 47%, #181818 50%,
            #0d0d0d 56%, #1a1a1a 59%, #0d0d0d 65%, #181818 68%,
            #0d0d0d 75%, #1a1a1a 78%, #111111 100%)`,
          boxShadow: isPlaying
            ? `0 0 0 2px ${hex}, 0 8px 32px ${hex}55, inset 0 0 0 1px #222`
            : '0 4px 24px rgba(0,0,0,0.7), inset 0 0 0 1px #222',
        }}
      >
        {/* Center label — spins with the disc */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div
            className="w-[88px] h-[88px] rounded-full flex flex-col items-center justify-center"
            style={{ background: labelBg }}
          >
            {(isPlaying || showLabel) && (
              emoji ? (
                <span className="text-xl leading-none mb-0.5">{emoji}</span>
              ) : (
                <span className="text-white text-[9px] font-bold tracking-widest uppercase opacity-80">
                  {topText}
                </span>
              )
            )}
            {(isPlaying || showLabel) && (
              <span className="text-white/60 text-[7px] tracking-wide mt-0.5">{bottomText}</span>
            )}
            {/* Center hole */}
            <div className="w-2.5 h-2.5 rounded-full bg-gray-950 mt-1" />
          </div>
        </div>
      </div>

      {/* Play overlay — shown only when paused, does NOT spin */}
      {!isPlaying && (
        <div className="absolute inset-0 rounded-full flex items-center justify-center
                        bg-black/30 hover:bg-black/40 transition-colors">
          <div
            className="w-14 h-14 rounded-full flex items-center justify-center shadow-lg transition-colors"
            style={{ background: glowColor }}
          >
            <Play className="w-6 h-6 text-white ml-0.5" />
          </div>
        </div>
      )}
    </div>
  );
}
