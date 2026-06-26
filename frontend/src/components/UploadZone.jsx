import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Upload, Music, FileAudio } from 'lucide-react';
import MusicLoader from './MusicLoader.jsx';
import { analyzeUpload } from '../api/client.js';

export default function UploadZone({ onResult }) {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);

  const handleFile = useCallback((f) => {
    const ok = ['audio/wav', 'audio/mpeg', 'audio/mp3', 'audio/x-wav'];
    if (!ok.includes(f.type)) { setError('Please choose a .wav or .mp3 file.'); return; }
    if (f.size > 50 * 1024 * 1024) { setError('That file is over 50 MB.'); return; }
    setError(null);
    setFile(f);
  }, []);

  const handleDrop = (e) => {
    e.preventDefault(); setIsDragging(false);
    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setIsAnalyzing(true); setError(null); setProgress(0);
    try {
      const result = await analyzeUpload(file, setProgress);
      onResult(result, file);
    } catch (err) {
      const detail = err.response?.data?.detail ?? '';
      setError(detail || 'Could not analyse that file. Please try again.');
    } finally { setIsAnalyzing(false); }
  };

  if (isAnalyzing) {
    return (
      <div className="card p-10 max-w-xl mx-auto">
        <MusicLoader text={progress < 100 ? `Uploading… ${progress}%` : 'Reading the mood…'} />
        <div className="mt-2 h-1.5 bg-line rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-clay rounded-full"
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-xl mx-auto">
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`relative px-6 py-10 text-center rounded-xl2 border border-dashed transition-colors cursor-pointer
          ${isDragging
            ? 'border-clay bg-clay-wash'
            : 'border-line-strong bg-card hover:border-ink-faint'}`}
      >
        <input
          type="file" accept=".wav,.mp3,audio/*"
          onChange={(e) => e.target.files[0] && handleFile(e.target.files[0])}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
        />
        <div className="flex flex-col items-center gap-3 pointer-events-none">
          {file ? (
            <>
              <span className="w-12 h-12 rounded-lg bg-clay-wash flex items-center justify-center">
                <FileAudio className="w-6 h-6 text-clay" strokeWidth={2} />
              </span>
              <div>
                <p className="text-ink font-semibold">{file.name}</p>
                <p className="text-ink-soft text-sm">{(file.size / 1024 / 1024).toFixed(1)} MB · ready</p>
              </div>
            </>
          ) : (
            <>
              <span className="w-12 h-12 rounded-lg bg-paper border border-line flex items-center justify-center">
                <Upload className="w-6 h-6 text-ink-soft" strokeWidth={2} />
              </span>
              <div>
                <p className="text-ink font-medium">Drop an audio file</p>
                <p className="text-ink-soft text-sm mt-0.5">or click to browse · wav, mp3 · up to 50 MB</p>
              </div>
            </>
          )}
        </div>
      </div>

      {error && <p className="text-energetic text-sm text-center mt-3">{error}</p>}

      <button
        onClick={handleAnalyze}
        disabled={!file}
        className={`mt-3 w-full h-12 rounded-xl2 font-semibold transition-colors flex items-center justify-center gap-2
          ${file
            ? 'bg-clay hover:bg-clay-dark text-white cursor-pointer'
            : 'bg-line text-ink-faint cursor-not-allowed'}`}
      >
        <Music className="w-4 h-4" strokeWidth={2.25} />
        Read its mood
      </button>
    </div>
  );
}
