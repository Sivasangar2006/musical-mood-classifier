import { useEffect, useRef, useState } from 'react';
import { Pause, ThumbsUp, Check } from 'lucide-react';
import VinylDisc from './VinylDisc.jsx';
import ValenceArousalPlot from './ValenceArousalPlot.jsx';
import CorpusTracks from './CorpusTracks.jsx';
import { submitVAFeedback } from '../api/client.js';

const MOODS = ['Happy', 'Energetic', 'Angry', 'Sad', 'Relaxed'];

const GRADIENTS = {
  Happy:     'from-yellow-400 to-orange-400',
  Energetic: 'from-red-500 to-pink-500',
  Angry:     'from-purple-600 to-red-600',
  Sad:       'from-blue-500 to-indigo-500',
  Relaxed:   'from-green-400 to-emerald-400',
};

const LABEL_BG = {
  Happy:     'radial-gradient(circle, #d97706, #92400e)',
  Energetic: 'radial-gradient(circle, #dc2626, #9f1239)',
  Angry:     'radial-gradient(circle, #7c3aed, #6b21a8)',
  Sad:       'radial-gradient(circle, #2563eb, #1e3a8a)',
  Relaxed:   'radial-gradient(circle, #059669, #065f46)',
};

const GLOW_COLOR = {
  Happy:     '#d97706',
  Energetic: '#ef4444',
  Angry:     '#7c3aed',
  Sad:       '#3b82f6',
  Relaxed:   '#10b981',
};

export default function MoodResult({ result, audioFile, audioUrl, onReset }) {
  const audioRef = useRef(null);
  const [show, setShow] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrent] = useState(0);
  const [duration, setDuration] = useState(0);
  const [srcUrl, setSrcUrl] = useState(null);
  const [fbState, setFbState] = useState('idle');  // idle | correcting | done

  // Resolve the audio source: an uploaded File becomes an object URL; a selected
  // iTunes track already has a preview URL we can play directly.
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

  useEffect(() => { setTimeout(() => setShow(true), 50); }, []);

  if (!result) return null;

  const grad    = GRADIENTS[result.mood]  || 'from-violet-500 to-purple-500';
  const labelBg = LABEL_BG[result.mood]   || 'radial-gradient(circle, #5b21b6, #3b0764)';
  const glow    = GLOW_COLOR[result.mood] || '#7c3aed';
  const hasVA    = typeof result.valence === 'number';

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) { audioRef.current.pause(); setIsPlaying(false); }
    else           { audioRef.current.play().catch(() => {}); setIsPlaying(true); }
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
    <div className={`w-full max-w-xl mx-auto transition-all duration-700 ${show ? 'opacity-100 scale-100' : 'opacity-0 scale-95'}`}>
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 md:p-10">

        <audio ref={audioRef} src={srcUrl || ''} preload="auto" className="hidden" />

        {/* Vinyl disc + scrubber */}
        {srcUrl && (
          <div className="mb-6">
            <VinylDisc
              isPlaying={isPlaying}
              onToggle={togglePlay}
              labelBg={labelBg}
              glowColor={glow}
              emoji={result.mood_emoji}
              bottomText={result.mood}
            />
            <div className="h-2 bg-gray-800 rounded-full cursor-pointer group relative mt-4" onClick={seekTo}>
              <div className="h-full rounded-full" style={{ width: duration ? `${(currentTime / duration) * 100}%` : '0%', background: glow }}>
                <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-white shadow opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </div>
            <div className="flex justify-between text-gray-500 text-xs font-mono mt-1 mb-3">
              <span>{fmt(currentTime)}</span>
              <span>{duration ? fmt(duration) : '0:00'}</span>
            </div>
            {isPlaying && (
              <div className="flex justify-center">
                <button onClick={togglePlay} className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: glow }}>
                  <Pause className="w-4 h-4 text-white" />
                </button>
              </div>
            )}
            <div className="border-t border-gray-800 mt-5 mb-5" />
          </div>
        )}

        {/* Track title (when analysing an iTunes selection) */}
        {result.title && (
          <p className="text-center text-gray-400 text-sm mb-2">
            <span className="text-white font-medium">{result.title}</span>
            {result.artist ? ` — ${result.artist}` : ''}
          </p>
        )}

        {/* Mood name + description + quadrant */}
        <div className="text-center mb-6">
          {!srcUrl && (
            <div className="text-7xl md:text-8xl mb-4 animate-bounce" style={{ animationDuration: '2s' }}>
              {result.mood_emoji}
            </div>
          )}
          <h2 className={`text-4xl md:text-5xl font-display font-bold gradient-text bg-gradient-to-r ${grad}`}>
            {result.mood}
          </h2>
          <p className="text-gray-400 mt-2 text-lg">{result.mood_description}</p>
          {result.quadrant && (
            <span className="inline-block mt-3 text-xs font-mono text-gray-500 bg-gray-800/60 px-3 py-1 rounded-full">
              {result.quadrant}
            </span>
          )}
        </div>

        {/* Valence/arousal circumplex */}
        {hasVA && (
          <div className="mb-8">
            <ValenceArousalPlot
              valence={result.valence}
              arousal={result.arousal}
              mood={result.mood}
              color={glow}
              similar={result.similar}
            />
          </div>
        )}

        {/* Confidence */}
        <div className="mb-2">
          <div className="flex justify-between items-center mb-2">
            <span className="text-gray-400 text-sm font-medium">Consistency</span>
            <span className="text-white font-bold text-lg">{(result.confidence * 100).toFixed(1)}%</span>
          </div>
          <div className="h-3 bg-gray-800 rounded-full overflow-hidden">
            <div className={`h-full bg-gradient-to-r ${grad} rounded-full transition-all duration-[1500ms] ease-out`}
              style={{ width: show ? `${result.confidence * 100}%` : '0%' }} />
          </div>
          {result.n_segments && (
            <p className="text-gray-600 text-[11px] mt-1">
              from {result.n_segments} time segments · agreement-based
            </p>
          )}
        </div>

        {/* Human-in-the-loop feedback — every verdict becomes a training example */}
        {result.analysis_id && (
          <div className="mt-6 mb-2 rounded-xl bg-gray-800/40 border border-gray-800 p-4">
            {fbState === 'done' ? (
              <p className="text-center text-emerald-400 text-sm flex items-center justify-center gap-2">
                <Check className="w-4 h-4" /> Thanks — the model learns from this.
              </p>
            ) : fbState === 'correcting' ? (
              <div className="text-center">
                <p className="text-gray-400 text-sm mb-3">What mood is it really?</p>
                <div className="flex flex-wrap justify-center gap-2">
                  {MOODS.map((m) => (
                    <button key={m} onClick={() => sendFeedback(false, m)}
                      className="px-3 py-1.5 rounded-full text-xs font-medium bg-gray-800 text-gray-300
                                 border border-gray-700 hover:border-violet-500 hover:text-white transition-colors">
                      {m}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center gap-3">
                <span className="text-gray-400 text-sm">Is <span className="text-white font-medium">{result.mood}</span> right?</span>
                <button onClick={() => sendFeedback(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                             bg-gray-800 text-gray-300 hover:bg-emerald-700 hover:text-white transition-colors">
                  <ThumbsUp className="w-3.5 h-3.5" /> Yes
                </button>
                <button onClick={() => setFbState('correcting')}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-800 text-gray-300
                             hover:bg-gray-700 hover:text-white transition-colors">
                  Fix it
                </button>
              </div>
            )}
          </div>
        )}

        {/* Similar songs from the corpus */}
        {result.similar?.length > 0 && (
          <>
            <div className="border-t border-gray-800 mt-8" />
            <CorpusTracks
              tracks={result.similar}
              heading="Songs that feel like this"
              subheading="Nearest neighbours in emotion space · 30s previews"
              accent={glow}
            />
          </>
        )}

        {/* Model badge */}
        <div className="mt-6 flex justify-center">
          <span className="text-gray-700 text-xs font-mono bg-gray-800/50 px-3 py-1 rounded-full">
            🎚️ CLAP + valence/arousal
          </span>
        </div>

        <button onClick={onReset}
          className="mt-6 w-full py-3.5 rounded-xl border border-gray-700 text-gray-400 hover:border-gray-500 hover:text-white hover:bg-gray-800 transition-all duration-200 font-medium">
          ← Analyze Another Song
        </button>
      </div>
    </div>
  );
}
