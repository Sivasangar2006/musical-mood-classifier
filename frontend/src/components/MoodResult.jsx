import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { Play, Pause, ThumbsUp, Check, ArrowLeft } from 'lucide-react';
import ValenceArousalPlot from './ValenceArousalPlot.jsx';
import CorpusTracks from './CorpusTracks.jsx';
import { submitVAFeedback } from '../api/client.js';
import { cardIn, ease } from '../lib/motion.js';

const MOODS = ['Happy', 'Energetic', 'Angry', 'Sad', 'Relaxed'];

// Mood colours, tuned for contrast on a light surface. Used only as data accents.
const MOOD_COLOR = {
  Happy: '#C98A12', Energetic: '#D6294B', Angry: '#7E3CC0', Sad: '#2563EB', Relaxed: '#0E8C63',
};

export default function MoodResult({ result, audioFile, audioUrl, onReset }) {
  const audioRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrent] = useState(0);
  const [duration, setDuration] = useState(0);
  const [srcUrl, setSrcUrl] = useState(null);
  const [fbState, setFbState] = useState('idle'); // idle | correcting | done

  useEffect(() => {
    if (audioFile) {
      const url = URL.createObjectURL(audioFile);
      setSrcUrl(url);
      return () => URL.revokeObjectURL(url);
    }
    if (audioUrl) setSrcUrl(audioUrl);
  }, [audioFile, audioUrl]);

  useEffect(() => {
    const a = audioRef.current;
    if (!a || !srcUrl) return;
    const onTime = () => setCurrent(a.currentTime);
    const onMeta = () => setDuration(a.duration);
    const onEnded = () => setIsPlaying(false);
    a.addEventListener('timeupdate', onTime);
    a.addEventListener('loadedmetadata', onMeta);
    a.addEventListener('ended', onEnded);
    if (a.readyState >= 1) setDuration(a.duration);
    a.play().catch(() => {});
    setIsPlaying(true);
    return () => {
      a.removeEventListener('timeupdate', onTime);
      a.removeEventListener('loadedmetadata', onMeta);
      a.removeEventListener('ended', onEnded);
      a.pause();
    };
  }, [srcUrl]);

  if (!result) return null;

  const color = MOOD_COLOR[result.mood] || '#C2553A';
  const hasVA = typeof result.valence === 'number';

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) { audioRef.current.pause(); setIsPlaying(false); }
    else { audioRef.current.play().catch(() => {}); setIsPlaying(true); }
  };

  const seekTo = (e) => {
    if (!audioRef.current || !duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    audioRef.current.currentTime = ((e.clientX - rect.left) / rect.width) * duration;
  };

  const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

  const sendFeedback = async (correct, correctedMood = null) => {
    setFbState('done');
    if (!result.analysis_id) return;
    try {
      await submitVAFeedback(result.analysis_id, { correct, corrected_mood: correctedMood });
    } catch { /* non-blocking */ }
  };

  return (
    <motion.div variants={cardIn} initial="hidden" animate="show" className="w-full max-w-xl mx-auto">
      <button
        onClick={onReset}
        className="flex items-center gap-1.5 text-ink-soft hover:text-ink text-sm font-medium mb-4 cursor-pointer transition-colors"
      >
        <ArrowLeft className="w-4 h-4" strokeWidth={2} /> New search
      </button>

      <div className="card p-6 md:p-8">
        <audio ref={audioRef} src={srcUrl || ''} preload="auto" className="hidden" />

        {/* Now playing */}
        {srcUrl && (
          <div className="flex items-center gap-4 mb-7">
            <button
              onClick={togglePlay}
              className="w-14 h-14 rounded-xl2 flex items-center justify-center shrink-0 cursor-pointer transition-transform active:scale-95"
              style={{ background: color }}
            >
              {isPlaying ? <Pause className="w-6 h-6 text-white" /> : <Play className="w-6 h-6 text-white ml-0.5" />}
            </button>
            <div className="flex-1 min-w-0">
              {result.title && (
                <p className="text-ink font-semibold truncate">{result.title}</p>
              )}
              {result.artist && <p className="text-ink-soft text-sm truncate">{result.artist}</p>}
              <div className="mt-2 h-1.5 bg-line rounded-full cursor-pointer relative" onClick={seekTo}>
                <div className="h-full rounded-full" style={{ width: duration ? `${(currentTime / duration) * 100}%` : '0%', background: color }} />
              </div>
              <div className="flex justify-between text-ink-faint text-[11px] font-medium mt-1">
                <span>{fmt(currentTime)}</span>
                <span>{duration ? fmt(duration) : '0:00'}</span>
              </div>
            </div>
          </div>
        )}

        {/* Mood verdict */}
        <div className="text-center mb-7">
          <p className="text-ink-soft text-xs uppercase tracking-wide font-semibold">This song feels</p>
          <motion.h2
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease, delay: 0.1 }}
            className="font-display text-5xl font-bold mt-1 tracking-tight"
            style={{ color }}
          >
            {result.mood}
          </motion.h2>
          {result.mood_description && (
            <p className="text-ink-soft mt-1.5">{result.mood_description}</p>
          )}
          {result.quadrant && (
            <span
              className="inline-block mt-3 text-xs font-medium px-2.5 py-1 rounded-full border"
              style={{ color, borderColor: `${color}40`, background: `${color}12` }}
            >
              {result.quadrant}
            </span>
          )}
        </div>

        {/* Circumplex */}
        {hasVA && (
          <div className="mb-7">
            <ValenceArousalPlot
              valence={result.valence}
              arousal={result.arousal}
              mood={result.mood}
              color={color}
              similar={result.similar}
            />
          </div>
        )}

        {/* Confidence */}
        <div className="mb-2">
          <div className="flex justify-between items-baseline mb-1.5">
            <span className="text-ink-soft text-sm font-medium">Confidence</span>
            <span className="text-ink font-bold">{(result.confidence * 100).toFixed(0)}%</span>
          </div>
          <div className="h-2 bg-line rounded-full overflow-hidden">
            <motion.div
              className="h-full rounded-full"
              style={{ background: color }}
              initial={{ width: 0 }}
              animate={{ width: `${result.confidence * 100}%` }}
              transition={{ duration: 1, ease, delay: 0.3 }}
            />
          </div>
        </div>

        {/* Feedback */}
        {result.analysis_id && (
          <div className="mt-6 rounded-xl2 bg-paper border border-line p-4">
            {fbState === 'done' ? (
              <p className="text-center text-relaxed text-sm font-medium flex items-center justify-center gap-2">
                <Check className="w-4 h-4" /> Thanks — that helps the model improve.
              </p>
            ) : fbState === 'correcting' ? (
              <div className="text-center">
                <p className="text-ink-soft text-sm mb-3">What does it actually feel like?</p>
                <div className="flex flex-wrap justify-center gap-2">
                  {MOODS.map((m) => (
                    <button key={m} onClick={() => sendFeedback(false, m)}
                      className="px-3 py-1.5 rounded-lg text-sm font-medium bg-card text-ink border border-line
                                 hover:border-clay hover:text-clay transition-colors cursor-pointer">
                      {m}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center gap-3 flex-wrap">
                <span className="text-ink-soft text-sm">Does <span className="text-ink font-medium">{result.mood}</span> sound right?</span>
                <button onClick={() => sendFeedback(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium
                             bg-card border border-line text-ink hover:border-relaxed hover:text-relaxed transition-colors cursor-pointer">
                  <ThumbsUp className="w-3.5 h-3.5" /> Yes
                </button>
                <button onClick={() => setFbState('correcting')}
                  className="px-3 py-1.5 rounded-lg text-sm font-medium bg-card border border-line text-ink-soft
                             hover:text-ink hover:border-line-strong transition-colors cursor-pointer">
                  Not quite
                </button>
              </div>
            )}
          </div>
        )}

        {/* Similar songs */}
        {result.similar?.length > 0 && (
          <div className="mt-7 pt-6 border-t border-line">
            <CorpusTracks
              tracks={result.similar}
              heading="Songs that feel like this"
              subheading="Closest matches in emotion · 30-second previews"
              accent={color}
            />
          </div>
        )}
      </div>
    </motion.div>
  );
}
