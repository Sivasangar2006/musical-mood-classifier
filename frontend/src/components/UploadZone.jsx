import { useState, useCallback } from 'react';
import { Upload, Music } from 'lucide-react';
import MusicLoader from './MusicLoader';

export default function UploadZone({ onResult }) {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);

  const handleFile = useCallback((f) => {
    const ok = ['audio/wav','audio/mpeg','audio/mp3','audio/x-wav'];
    if (!ok.includes(f.type)) { setError('Please upload a .wav or .mp3 file'); return; }
    if (f.size > 50*1024*1024) { setError('File too large. Max 50 MB.'); return; }
    setError(null);
    setFile(f);
  }, []);

  const handleDrop = (e) => {
    e.preventDefault(); setIsDragging(false);
    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
  };

  const handleInputChange = (e) => {
    if (e.target.files[0]) handleFile(e.target.files[0]);
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setIsAnalyzing(true); setError(null); setProgress(0);
    try {
      const { predictMood } = await import('../api/client.js');
      const result = await predictMood(file, setProgress);
      onResult(result, file);
    } catch (err) {
      setError(err.response?.data?.detail || 'Analysis failed. Is the backend running?');
    } finally { setIsAnalyzing(false); }
  };

  if (isAnalyzing) {
    return (
      <div className="card p-10 max-w-xl mx-auto animate-scale-in">
        <MusicLoader text={progress < 100 ? `Uploading… ${progress}%` : 'Analyzing mood…'} />
        <div className="mt-4 h-1.5 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-violet-500 to-fuchsia-500 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-xl mx-auto animate-fade-in-up">
      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`
          relative p-10 text-center transition-all duration-200 cursor-pointer rounded-2xl
          border-2 border-dashed
          ${isDragging
            ? 'border-violet-500 bg-violet-500/10'
            : 'border-gray-700 bg-gray-900 hover:border-gray-600 hover:bg-gray-800/80'}
        `}
      >
        <input
          type="file" accept=".wav,.mp3,audio/*"
          onChange={handleInputChange}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
        />
        <div className="flex flex-col items-center gap-4 pointer-events-none">
          {file ? (
            <>
              <div className="w-16 h-16 rounded-2xl bg-violet-900/50 border border-violet-700 flex items-center justify-center">
                <Music className="w-8 h-8 text-violet-400" />
              </div>
              <div>
                <p className="text-white font-semibold text-lg">{file.name}</p>
                <p className="text-gray-500 text-sm">{(file.size/1024/1024).toFixed(2)} MB</p>
              </div>
            </>
          ) : (
            <>
              <div className="w-16 h-16 rounded-2xl bg-gray-800 border border-gray-700 flex items-center justify-center">
                <Upload className="w-8 h-8 text-gray-500" />
              </div>
              <div>
                <p className="text-white font-medium text-lg">Drop your audio file here</p>
                <p className="text-gray-500 text-sm mt-1">or click to browse</p>
                <p className="text-gray-600 text-xs mt-3 font-mono">.wav  ·  .mp3  ·  max 50MB</p>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Mobile browse button */}
      <label className="mt-3 flex items-center justify-center gap-2 w-full py-3 rounded-xl
                        bg-gray-900 border border-gray-800 cursor-pointer hover:bg-gray-800 transition-colors md:hidden">
        <span>📁</span>
        <span className="text-gray-300 text-sm font-medium">Browse Files</span>
        <input type="file" accept=".wav,.mp3,audio/*" onChange={handleInputChange} className="hidden" />
      </label>

      {/* Error */}
      {error && (
        <div className="mt-3 p-3 bg-red-900/40 border border-red-800 rounded-xl animate-scale-in">
          <p className="text-red-400 text-sm text-center">{error}</p>
        </div>
      )}

      {/* Analyze button */}
      <button
        onClick={handleAnalyze}
        disabled={!file}
        className={`
          mt-5 w-full py-4 rounded-xl font-bold text-lg transition-all duration-200
          ${file
            ? 'bg-violet-600 hover:bg-violet-500 text-white shadow-lg'
            : 'bg-gray-800 text-gray-600 cursor-not-allowed border border-gray-700'}
        `}
      >
        🎵 Analyze Mood
      </button>
    </div>
  );
}
