export default function HeroSection() {
  return (
    <section className="text-center pt-16 pb-12 px-4 animate-fade-in-up">
      {/* Decorative badge */}


      <h1 className="text-4xl md:text-6xl lg:text-7xl font-display font-bold text-white leading-tight mb-5 tracking-tight">
        What's the{' '}
        <span className="gradient-text from-violet-400 via-fuchsia-400 to-pink-400 animated-gradient bg-[length:200%_auto]">
          mood
        </span>
        <br />of your music?
      </h1>

      <p className="text-gray-400 text-lg md:text-xl max-w-xl mx-auto leading-relaxed font-light">
        Upload a song and discover its{' '}
        <span className="text-gray-200 font-medium">emotional fingerprint</span>
        {' '}— then find acoustically similar tracks
      </p>

      {/* Tech badges */}
      <div className="flex flex-wrap items-center justify-center gap-2 mt-6">
        {['ResNet18', 'FAISS', 'SVM', 'Librosa', 'Last.fm'].map((t) => (
          <span
            key={t}
            className="text-xs font-mono text-gray-600 bg-gray-900 border border-gray-800
                       px-2.5 py-1 rounded-full"
          >
            {t}
          </span>
        ))}
      </div>
    </section>
  );
}
