import { useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import Navbar from './components/Navbar';
import HeroSection from './components/HeroSection';
import SongSearch from './components/SongSearch';
import UploadZone from './components/UploadZone';
import MoodResult from './components/MoodResult';
import VibeSearch from './components/VibeSearch';
import MoodBrowser from './components/MoodBrowser';
import HistoryPanel from './components/HistoryPanel';

export default function App() {
  const [result, setResult] = useState(null);
  const [audioFile, setAudioFile] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [showHistory, setShowHistory] = useState(false);

  // `source` is either an uploaded File or a selected track ({ preview_url }).
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
    <div className="min-h-screen bg-paper">
      <Navbar onReset={handleReset} onHistory={() => setShowHistory(true)} />
      <HistoryPanel open={showHistory} onClose={() => setShowHistory(false)} />

      <main>
        <div className="max-w-3xl mx-auto px-4 sm:px-6">
          <AnimatePresence mode="wait">
            {!result ? (
              <div key="search">
                <HeroSection />
                <SongSearch onResult={handleResult} />

                <div className="max-w-xl mx-auto mt-8">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="flex-1 border-t border-line" />
                    <span className="text-ink-faint text-xs uppercase tracking-wide font-medium">or upload a file</span>
                    <div className="flex-1 border-t border-line" />
                  </div>
                  <UploadZone onResult={handleResult} />
                </div>
              </div>
            ) : (
              <div key="result" className="pt-10 pb-4">
                <MoodResult
                  result={result}
                  audioFile={audioFile}
                  audioUrl={audioUrl}
                  onReset={handleReset}
                />
              </div>
            )}
          </AnimatePresence>
        </div>

        {!result && (
          <>
            <div className="max-w-2xl mx-auto px-4 sm:px-6 pt-12"><div className="border-t border-line" /></div>
            <VibeSearch />
            <div className="max-w-2xl mx-auto px-4 sm:px-6"><div className="border-t border-line" /></div>
            <MoodBrowser />
          </>
        )}

        <footer className="border-t border-line mt-8">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-2">
            <span className="font-display text-sm font-bold text-ink">MoodWave</span>
            <p className="text-ink-faint text-xs">Find the feeling in your music.</p>
          </div>
        </footer>
      </main>
    </div>
  );
}
