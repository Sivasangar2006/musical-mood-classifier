import { useState } from 'react';
import FloatingNotes from './components/FloatingNotes';
import Navbar from './components/Navbar';
import HeroSection from './components/HeroSection';
import UploadZone from './components/UploadZone';
import MoodResult from './components/MoodResult';
import DemoSection from './components/DemoSection';

export default function App() {
  const [result, setResult] = useState(null);
  const [audioFile, setAudioFile] = useState(null);

  const handleResult = (res, file) => {
    setResult(res);
    setAudioFile(file);
  };

  const handleReset = () => {
    setResult(null);
    setAudioFile(null);
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
              <UploadZone onResult={handleResult} />
            </>
          ) : (
            <div className="pt-12">
              <MoodResult result={result} audioFile={audioFile} onReset={handleReset} />
            </div>
          )}
        </div>

        <div className="max-w-5xl mx-auto px-4 py-8">
          <div className="border-t border-gray-800" />
        </div>

        <DemoSection />

        <footer className="text-center py-10 border-t border-gray-800 mt-10">
          <p className="text-gray-600 text-sm">
            Built with 🎵 · Powered by ML + Librosa
          </p>
        </footer>
      </main>
    </div>
  );
}
