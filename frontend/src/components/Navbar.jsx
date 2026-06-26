import { motion, AnimatePresence } from 'framer-motion';
import { LogOut, Clock, AudioLines, Sun, Moon } from 'lucide-react';
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../auth/AuthContext.jsx';
import { useTheme } from '../theme/ThemeContext.jsx';

function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const dark = theme === 'dark';
  return (
    <button
      onClick={toggle}
      title={dark ? 'Switch to light' : 'Switch to dark'}
      aria-label="Toggle theme"
      className="w-9 h-9 rounded-lg border border-line text-ink-soft hover:text-ink hover:border-line-strong
                 flex items-center justify-center cursor-pointer transition-colors overflow-hidden"
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={theme}
          initial={{ y: 14, opacity: 0, rotate: -30 }}
          animate={{ y: 0, opacity: 1, rotate: 0 }}
          exit={{ y: -14, opacity: 0, rotate: 30 }}
          transition={{ duration: 0.2 }}
        >
          {dark ? <Sun className="w-4 h-4" strokeWidth={2} /> : <Moon className="w-4 h-4" strokeWidth={2} />}
        </motion.span>
      </AnimatePresence>
    </button>
  );
}

export default function Navbar({ onReset, onHistory }) {
  const { user, ready, loginWithGoogle, logout } = useAuth();
  const { theme } = useTheme();

  return (
    <header className="sticky top-0 z-50 bg-paper border-b border-line">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        <button onClick={onReset} className="flex items-center gap-2.5 cursor-pointer">
          <span className="w-9 h-9 rounded-lg bg-clay flex items-center justify-center">
            <AudioLines className="w-5 h-5 text-white" strokeWidth={2.25} />
          </span>
          <span className="font-display text-[20px] font-bold text-ink tracking-tight">MoodWave</span>
        </button>

        <div className="flex items-center gap-2 sm:gap-3">
          <button
            onClick={onHistory}
            className="flex items-center gap-1.5 px-3 h-9 rounded-lg text-sm font-medium text-ink-soft
                       hover:text-ink hover:bg-line/50 transition-colors cursor-pointer"
          >
            <Clock className="w-4 h-4" strokeWidth={2} />
            <span className="hidden sm:inline">History</span>
          </button>

          <ThemeToggle />

          {ready && (user ? (
            <div className="flex items-center gap-2.5">
              {user.picture && (
                <img
                  src={user.picture}
                  alt={user.name || 'you'}
                  className="w-8 h-8 rounded-full border border-line"
                  referrerPolicy="no-referrer"
                />
              )}
              <span className="text-ink text-sm font-medium hidden sm:block max-w-[140px] truncate">
                {user.name}
              </span>
              <button
                onClick={logout}
                title="Sign out"
                className="w-9 h-9 rounded-lg border border-line text-ink-soft hover:text-ink hover:border-line-strong
                           flex items-center justify-center cursor-pointer transition-colors"
              >
                <LogOut className="w-4 h-4" strokeWidth={2} />
              </button>
            </div>
          ) : (
            <motion.div key={theme} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.25 }}>
              <GoogleLogin
                onSuccess={(cr) => loginWithGoogle(cr.credential).catch(() => {})}
                onError={() => {}}
                theme={theme === 'dark' ? 'filled_black' : 'outline'}
                shape="pill"
                text="signin"
                size="medium"
              />
            </motion.div>
          ))}
        </div>
      </div>
    </header>
  );
}
