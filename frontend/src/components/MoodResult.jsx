import { useEffect, useRef, useState } from 'react';
import { Pause, ThumbsUp, ThumbsDown } from 'lucide-react';
import VinylDisc from './VinylDisc.jsx';
import SimilarSongs from './SimilarSongs.jsx';
import LastFmRecommendations from './LastFmRecommendations.jsx';

const GRADIENTS = {
  Happy:     'from-yellow-400 to-orange-400',
  Energetic: 'from-red-500 to-pink-500',
  Angry:     'from-purple-600 to-red-600',
  Sad:       'from-blue-500 to-indigo-500',
  Relaxed:   'from-green-400 to-emerald-400',
};

const BORDER = {
  Happy:     'border-yellow-800',
  Energetic: 'border-red-900',
  Angry:     'border-purple-900',
  Sad:       'border-blue-900',
  Relaxed:   'border-emerald-900',
};

// Mood-tinted label colors for the disc center
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

export default function MoodResult({ result, audioFile, onReset }) {
  const audioRef = useRef(null);
  const [show, setShow] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrent] = useState(0);
  const [duration, setDuration] = useState(0);
  const [srcUrl, setSrcUrl] = useState(null);
  const [feedback, setFeedback] = useState(null);  // true | false | null

  // Create object URL for the file
  useEffect(() => {
    if (!audioFile) return;
    const url = URL.createObjectURL(audioFile);
    setSrcUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [audioFile]);

  // Wire up events + autoplay once we have a src.
  // Audio element is always mounted, so audioRef.current is guaranteed here.
  useEffect(() => {
    const a = audioRef.current;
    if (!a || !srcUrl) return;

    const onTime = () => setCurrent(a.currentTime);
    const onMeta = () => setDuration(a.duration);
    const onEnded = () => setIsPlaying(false);

    a.addEventListener('timeupdate', onTime);
    a.addEventListener('loadedmetadata', onMeta);
    a.addEventListener('ended', onEnded);

    // Metadata may have already loaded by the time this effect runs
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

  const sorted = Object.entries(result.probabilities).sort(([, a], [, b]) => b - a);
  const grad    = GRADIENTS[result.mood]  || 'from-violet-500 to-purple-500';
  const border  = BORDER[result.mood]     || 'border-gray-700';
  const labelBg = LABEL_BG[result.mood]   || 'radial-gradient(circle, #5b21b6, #3b0764)';
  const glow    = GLOW_COLOR[result.mood] || '#7c3aed';

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) { audioRef.current.pause(); setIsPlaying(false); }
    else           { audioRef.current.play().catch(() => {}); setIsPlaying(true); }
  };

  const submitFeedback = async (correct) => {
    setFeedback(correct);
    try {
      const BASE = import.meta.env.VITE_API_URL || '/api';
      await fetch(`${BASE}/feedback/${result.prediction_id}?correct=${correct}`, {
        method: 'POST',
      });
    } catch { /* silent */ }
  };

  const seekTo = (e) => {
    if (!audioRef.current || !duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    audioRef.current.currentTime = ((e.clientX - rect.left) / rect.width) * duration;
  };

  const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

  return (
    <div className={`w-full max-w-xl mx-auto transition-all duration-700 ${show ? 'opacity-100 scale-100' : 'opacity-0 scale-95'}`}>
      <div className={`bg-gray-900 border ${border} rounded-2xl p-8 md:p-10`}>

        {/* Audio element always mounted so the ref is available when events are wired */}
        <audio ref={audioRef} src={srcUrl || ''} preload="auto" className="hidden" />

        {/* Vinyl disc */}
        {audioFile && (
          <div className="mb-6">
            <VinylDisc
              isPlaying={isPlaying}
              onToggle={togglePlay}
              labelBg={labelBg}
              glowColor={glow}
              emoji={result.mood_emoji}
              bottomText={result.mood}
            />

            {/* Progress bar */}
            <div
              className="h-2 bg-gray-800 rounded-full cursor-pointer group relative mt-4"
              onClick={seekTo}
            >
              <div
                className="h-full rounded-full relative transition-none"
                style={{
                  width: duration ? `${(currentTime / duration) * 100}%` : '0%',
                  background: glow,
                }}
              >
                <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 rounded-full
                                bg-white shadow opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </div>
            <div className="flex justify-between text-gray-500 text-xs font-mono mt-1 mb-3">
              <span>{fmt(currentTime)}</span>
              <span>{duration ? fmt(duration) : '0:00'}</span>
            </div>

            {/* Pause button — only visible while playing so it doesn't duplicate the disc overlay */}
            {isPlaying && (
              <div className="flex justify-center">
                <button
                  onClick={togglePlay}
                  className="w-10 h-10 rounded-full flex items-center justify-center transition-colors"
                  style={{ background: glow }}
                >
                  <Pause className="w-4 h-4 text-white" />
                </button>
              </div>
            )}

            <div className="border-t border-gray-800 mt-5 mb-5" />
          </div>
        )}

        {/* Mood name + description */}
        <div className="text-center mb-8">
          {!audioFile && (
            <div className="text-7xl md:text-8xl mb-4 animate-bounce" style={{ animationDuration: '2s' }}>
              {result.mood_emoji}
            </div>
          )}
          <h2 className={`text-4xl md:text-5xl font-display font-bold gradient-text bg-gradient-to-r ${grad}`}>
            {result.mood}
          </h2>
          <p className="text-gray-400 mt-2 text-lg">{result.mood_description}</p>
        </div>

        {/* Feedback */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <span className="text-gray-500 text-xs">Was this correct?</span>
          <button
            onClick={() => submitFeedback(true)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
              ${feedback === true
                ? 'bg-emerald-700 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-emerald-400'}`}
          >
            <ThumbsUp className="w-3.5 h-3.5" /> Yes
          </button>
          <button
            onClick={() => submitFeedback(false)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
              ${feedback === false
                ? 'bg-red-900 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-red-400'}`}
          >
            <ThumbsDown className="w-3.5 h-3.5" /> No
          </button>
          {feedback !== null && (
            <span className="text-gray-600 text-xs">
              {feedback ? 'Thanks!' : 'Got it, we\'ll learn from this'}
            </span>
          )}
        </div>

        {/* Confidence */}
        <div className="mb-8">
          <div className="flex justify-between items-center mb-2">
            <span className="text-gray-400 text-sm font-medium">Confidence</span>
            <span className="text-white font-bold text-lg">{(result.confidence * 100).toFixed(1)}%</span>
          </div>
          <div className="h-3 bg-gray-800 rounded-full overflow-hidden">
            <div
              className={`h-full bg-gradient-to-r ${grad} rounded-full transition-all duration-[1500ms] ease-out`}
              style={{ width: show ? `${result.confidence * 100}%` : '0%' }}
            />
          </div>
        </div>

        {/* All moods */}
        <div>
          <p className="text-gray-500 text-xs uppercase tracking-widest font-semibold mb-4">All Moods</p>
          <div className="space-y-3">
            {sorted.map(([mood, prob], idx) => {
              const mg = GRADIENTS[mood] || 'from-gray-500 to-gray-600';
              const isPrimary = mood === result.mood;
              return (
                <div key={mood} style={{ animationDelay: `${idx * 120}ms` }} className="animate-fade-in-up">
                  <div className="flex justify-between text-sm mb-1.5">
                    <span className={isPrimary ? 'text-white font-semibold' : 'text-gray-400'}>{mood}</span>
                    <span className={isPrimary ? 'text-white font-semibold' : 'text-gray-500 font-mono text-xs'}>
                      {(prob * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ease-out ${
                        isPrimary ? `bg-gradient-to-r ${mg}` : 'bg-gray-700'
                      }`}
                      style={{
                        width: show ? `${prob * 100}%` : '0%',
                        transitionDuration: `${800 + idx * 200}ms`,
                        transitionDelay: `${idx * 100}ms`,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* FAISS similar songs — only present when CNN endpoint was used */}
        {result.similar_songs?.length > 0 && (
          <>
            <div className="border-t border-gray-800 mt-8" />
            <SimilarSongs songs={result.similar_songs} />
          </>
        )}

        {/* Last.fm mood-based recommendations */}
        <div className="border-t border-gray-800 mt-8" />
        <LastFmRecommendations mood={result.mood} />

        {/* Model badge */}
        {result.model && (
          <div className="mt-6 flex justify-center">
            <span className="text-gray-700 text-xs font-mono bg-gray-800/50 px-3 py-1 rounded-full">
              {result.model === 'cnn' ? '🧠 ResNet18 + FAISS' : '📊 SVM + Librosa'}
            </span>
          </div>
        )}

        {/* Reset */}
        <button
          onClick={onReset}
          className="mt-8 w-full py-3.5 rounded-xl border border-gray-700 text-gray-400
                     hover:border-gray-500 hover:text-white hover:bg-gray-800 transition-all duration-200 font-medium"
        >
          ← Analyze Another Song
        </button>
      </div>
    </div>
  );
}
