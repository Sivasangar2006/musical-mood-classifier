import { useState } from 'react';
import FloatingNotes from './components/FloatingNotes';
import Navbar from './components/Navbar';
import HeroSection from './components/HeroSection';
import SongSearch from './components/SongSearch';
import UploadZone from './components/UploadZone';
import MoodResult from './components/MoodResult';
import VibeSearch from './components/VibeSearch';
import MoodBrowser from './components/MoodBrowser';
import DemoSection from './components/DemoSection';
import ModelMetrics from './components/ModelMetrics';

export default function App() {
  const [result, setResult] = useState(null);
  const [audioFile, setAudioFile] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);

  // `source` is either an uploaded File or a selected iTunes track ({preview_url}).
  const handleResult = (res, source) => {
    setResult(res);
    if (source instanceof File) {
      setAudioFile(source);
      setAudioUrl(null);
    } else if (source && source.preview_url) {
      setAudioUrl(source.preview_url);
      setAudioFile(null);
    }
  };

  const handleReset = () => {
    setResult(null);
    setAudioFile(null);
    setAudioUrl(null);
  };

  return (
    <div className="min-h-screen bg-gray-950 relative overflow-x-hidden">
      <FloatingNotes />
      <Navbar onReset={handleReset} />

      <main className="relative z-10">
        <div className="max-w-3xl mx-auto px-4">
          {!result ? (
            <>
              <HeroSection />
              <SongSearch onResult={handleResult} />

              {/* Secondary: upload your own audio file */}
              <div className="max-w-xl mx-auto mt-8">
                <div className="flex items-center gap-3 mb-5">
                  <div className="flex-1 border-t border-gray-800" />
                  <span className="text-gray-600 text-xs uppercase tracking-widest">or upload a file</span>
                  <div className="flex-1 border-t border-gray-800" />
                </div>
                <UploadZone onResult={handleResult} />
              </div>
            </>
          ) : (
            <div className="pt-12">
              <MoodResult
                result={result}
                audioFile={audioFile}
                audioUrl={audioUrl}
                onReset={handleReset}
              />
            </div>
          )}
        </div>

        <div className="max-w-5xl mx-auto px-4 py-8">
          <div className="border-t border-gray-800" />
        </div>

        <VibeSearch />

        <div className="max-w-5xl mx-auto px-4 py-4">
          <div className="border-t border-gray-800" />
        </div>

        <MoodBrowser />

        <div className="max-w-5xl mx-auto px-4 py-4">
          <div className="border-t border-gray-800" />
        </div>

        <DemoSection />

        <div className="max-w-5xl mx-auto px-4 py-4">
          <div className="border-t border-gray-800" />
        </div>

        <ModelMetrics />

        <footer className="text-center py-10 border-t border-gray-800 mt-10">
          <p className="text-gray-600 text-sm">
            Built with 🎵 · CLAP embeddings · valence/arousal regression · vector search
          </p>
        </footer>
      </main>
    </div>
  );
}
