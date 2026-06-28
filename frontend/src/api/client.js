import axios from 'axios';

// Dev: VITE_API_URL points at the local backend (see .env.local).
// Single-container deploy (e.g. HF Spaces): leave VITE_API_URL empty so the SPA
// calls the same origin it's served from (FastAPI serves both API and static).
const BASE_URL = import.meta.env.VITE_API_URL || '';

const client = axios.create({
    baseURL: BASE_URL,
    timeout: 300000, // 5 minutes — full song analysis can take a while
});

// Attach the session JWT (set at login) to every request.
client.interceptors.request.use((config) => {
    const token = localStorage.getItem('mw_token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
});

// ─── Auth ────────────────────────────────────────────────────────────────────

/** Exchange a Google ID token for an app session. Returns { token, user }. */
export const authGoogle = async (credential) => {
    const response = await client.post('/auth/google', { credential });
    return response.data;
};

/** Fetch the current user (401 if not signed in). */
export const getMe = async () => {
    const response = await client.get('/auth/me');
    return response.data;
};

// ─── Song search + analysis (CLAP valence/arousal engine) ────────────────────

/** Typeahead: search iTunes for a song/artist to analyse. */
export const searchSongs = async (q, limit = 10) => {
    const response = await client.get(`/recommendations/Happy/search`, { params: { q, limit } });
    return response.data.tracks;
};

/** Analyse an iTunes track by its 30s preview. Returns V/A, mood, confidence, similar songs. */
export const analyzeTrack = async (track) => {
    const response = await client.post('/analyze/track', {
        preview_url: track.preview_url,
        title: track.title,
        artist: track.artist,
    });
    return response.data;
};

/** Analyse an uploaded audio file. */
export const analyzeUpload = async (file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await client.post('/analyze/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
            if (onProgress && e.total) onProgress(Math.round((e.loaded * 100) / e.total));
        },
    });
    return response.data;
};

// ─── Discovery ───────────────────────────────────────────────────────────────

/** Songs the model placed nearest a mood in valence/arousal space. */
export const getVARecommendations = async (mood, k = 15) => {
    const response = await client.get(`/va/recommend/${mood}`, { params: { k } });
    return response.data;
};

/** Cross-modal text-to-mood search: describe a vibe, get songs that sound like it. */
export const searchByVibe = async (q, k = 12) => {
    const response = await client.get('/va/search', { params: { q, k } });
    return response.data;
};

// ─── Feedback + history ──────────────────────────────────────────────────────

/** Submit human feedback on an analysis (confirm or correct). Feeds continual learning. */
export const submitVAFeedback = async (analysisId, body) => {
    const response = await client.post(`/va/feedback/${analysisId}`, body);
    return response.data;
};

/** The signed-in user's analysed songs with their mood + confidence. */
export const getVAHistory = async (limit = 20) => {
    const response = await client.get('/va/history', { params: { limit } });
    return response.data;
};
