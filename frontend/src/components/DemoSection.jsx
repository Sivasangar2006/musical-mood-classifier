import { useRef, useState, useEffect } from 'react';
import { Pause, Loader2 } from 'lucide-react';
import { predictMood } from '../api/client.js';
import VinylDisc from './VinylDisc.jsx';

const GRADIENTS = {
  Happy: 'from-yellow-400 to-orange-400',
  Energetic: 'from-red-500 to-pink-500',
  Angry: 'from-purple-600 to-red-600',
  Sad: 'from-blue-500 to-indigo-500',
  Relaxed: 'from-green-400 to-emerald-400',
};

const DEMO_SONG_URL = '/demo-song.mp3';

export default function DemoSection() {
  const sectionRef = useRef(null);
  const audioRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrent] = useState(0);
  const [duration, setDuration] = useState(0);
  const [hasAudio, setHasAudio] = useState(true);
  const [visible, setVisible] = useState(false);

  const [prediction, setPrediction] = useState(null);
  const [predicting, setPredicting] = useState(false);
  const [predError, setPredError] = useState(null);
  const [hasFetched, setHasFetched] = useState(false);

  useEffect(() => {
    if (hasFetched || !hasAudio) return;
    const analyze = async () => {
      setPredicting(true);
      setPredError(null);
      try {
        const res = await fetch(DEMO_SONG_URL);
        if (!res.ok) { setHasAudio(false); return; }
        const blob = await res.blob();
        const file = new File([blob], 'demo-song.mp3', { type: 'audio/mpeg' });
        const result = await predictMood(file, () => {});
        setPrediction(result);
      } catch (err) {
        setPredError('Could not analyze demo song');
        console.error('Demo prediction error:', err);
      } finally {
        setPredicting(false);
        setHasFetched(true);
      }
    };
    analyze();
  }, [hasFetched, hasAudio]);

  useEffect(() => {
    const el = sectionRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        setVisible(entry.isIntersecting);
        if (entry.isIntersecting && audioRef.current && hasAudio) {
          audioRef.current.play()
            .then(() => setIsPlaying(true))
            .catch(() => setIsPlaying(false));
        } else if (!entry.isIntersecting && audioRef.current) {
          audioRef.current.pause();
          setIsPlaying(false);
        }
      },
      { threshold: 0.5 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [hasAudio]);

  useEffect(() => {
    const a = audioRef.current;
    if (!a) return;
    const onTime = () => setCurrent(a.currentTime);
    const onMeta = () => setDuration(a.duration);
    const onErr = () => setHasAudio(false);
    a.addEventListener('timeupdate', onTime);
    a.addEventListener('loadedmetadata', onMeta);
    a.addEventListener('error', onErr);
    return () => {
      a.removeEventListener('timeupdate', onTime);
      a.removeEventListener('loadedmetadata', onMeta);
      a.removeEventListener('error', onErr);
    };
  }, []);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) { audioRef.current.pause(); setIsPlaying(false); }
    else { audioRef.current.play().catch(() => {}); setIsPlaying(true); }
  };

  const seekTo = (e) => {
    if (!audioRef.current || !duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    audioRef.current.currentTime = pct * duration;
  };

  const fmt = (s) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  const mood = prediction?.mood || '—';
  const emoji = prediction?.mood_emoji || '🎵';
  const description = prediction?.mood_description || '';
  const confidence = prediction?.confidence || 0;
  const probabilities = prediction?.probabilities || {};
  const grad = GRADIENTS[mood] || 'from-violet-500 to-purple-500';
  const sorted = Object.entries(probabilities).sort(([, a], [, b]) => b - a);

  if (!hasAudio) return null;

  return (
    <section
      ref={sectionRef}
      className={`max-w-5xl mx-auto px-4 py-20 transition-all duration-700
                  ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
    >
      <div className="text-center mb-12">
        <h2 className="text-3xl md:text-4xl font-display font-bold text-white">
          Hear it in action
        </h2>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Player card */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 md:p-8 flex flex-col">
          <audio ref={audioRef} src={DEMO_SONG_URL} preload="metadata" loop />

          <VinylDisc isPlaying={isPlaying} onToggle={togglePlay} />

          <h3 className="text-white font-semibold text-lg text-center mb-4">The Life of Ram</h3>

          {/* Progress bar */}
          <div
            className="h-2 bg-gray-800 rounded-full cursor-pointer group mb-2 relative"
            onClick={seekTo}
          >
            <div
              className="h-full bg-violet-600 rounded-full relative"
              style={{ width: duration ? `${(currentTime / duration) * 100}%` : '0%' }}
            >
              <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3.5 h-3.5 rounded-full
                              bg-white shadow opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
          </div>
          <div className="flex justify-between text-gray-500 text-xs font-mono mb-4">
            <span>{fmt(currentTime)}</span>
            <span>{duration ? fmt(duration) : '0:00'}</span>
          </div>

          <button
            onClick={togglePlay}
            className="mx-auto w-12 h-12 rounded-full bg-violet-600 hover:bg-violet-500
                       flex items-center justify-center transition-colors shadow-lg"
          >
            {isPlaying
              ? <Pause className="w-5 h-5 text-white" />
              : <span className="w-5 h-5 text-white ml-0.5">▶</span>}
          </button>
        </div>

        {/* Mood result card */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 md:p-8 flex flex-col justify-center">
          {predicting ? (
            <div className="text-center py-10">
              <Loader2 className="w-10 h-10 text-violet-400 animate-spin mx-auto mb-4" />
              <p className="text-gray-400 text-sm">Analyzing demo song…</p>
            </div>
          ) : predError ? (
            <div className="text-center py-10">
              <p className="text-red-400 text-sm">{predError}</p>
              <p className="text-gray-600 text-xs mt-2">Make sure the backend is running on port 8000</p>
            </div>
          ) : prediction ? (
            <>
              <div className="text-center mb-6">
                <span className="text-5xl">{emoji}</span>
                <h3 className={`text-3xl font-display font-bold gradient-text bg-gradient-to-r ${grad} mt-2`}>
                  {mood}
                </h3>
                <p className="text-gray-400 text-sm mt-1">{description}</p>
              </div>

              <div className="mb-6">
                <div className="flex justify-between mb-1.5">
                  <span className="text-gray-500 text-xs uppercase tracking-wider font-semibold">Confidence</span>
                  <span className="text-white font-bold">{(confidence * 100).toFixed(1)}%</span>
                </div>
                <div className="h-2.5 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full bg-gradient-to-r ${grad} rounded-full transition-all duration-[2s] ease-out`}
                    style={{ width: visible ? `${confidence * 100}%` : '0%' }}
                  />
                </div>
              </div>

              <p className="text-gray-600 text-xs uppercase tracking-widest font-semibold mb-3">Breakdown</p>
              <div className="space-y-3">
                {sorted.map(([m, prob]) => {
                  const isPrimary = m === mood;
                  return (
                    <div key={m}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className={isPrimary ? 'text-white font-medium' : 'text-gray-500'}>{m}</span>
                        <span className={isPrimary ? 'text-white' : 'text-gray-600 font-mono text-xs'}>
                          {(prob * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-[2s] ease-out ${
                            isPrimary ? `bg-gradient-to-r ${GRADIENTS[m]}` : 'bg-gray-700'
                          }`}
                          style={{ width: visible ? `${prob * 100}%` : '0%' }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
            <div className="text-center py-10 text-gray-600 text-sm">
              <p>Waiting for analysis…</p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
