/**
 * AuthContext — holds the signed-in user + session token (Google OAuth).
 * The token is persisted in localStorage and attached to API requests by the
 * axios interceptor in api/client.js.
 */

import { createContext, useContext, useEffect, useState } from 'react';
import { authGoogle, getMe } from '../api/client.js';

const AuthCtx = createContext(null);
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  // Restore session on load.
  useEffect(() => {
    const token = localStorage.getItem('mw_token');
    if (!token) { setReady(true); return; }
    getMe()
      .then(setUser)
      .catch(() => localStorage.removeItem('mw_token'))
      .finally(() => setReady(true));
  }, []);

  const loginWithGoogle = async (credential) => {
    const data = await authGoogle(credential);
    localStorage.setItem('mw_token', data.token);
    setUser(data.user);
    return data.user;
  };

  const logout = () => {
    localStorage.removeItem('mw_token');
    setUser(null);
  };

  return (
    <AuthCtx.Provider value={{ user, ready, loginWithGoogle, logout }}>
      {children}
    </AuthCtx.Provider>
  );
}
