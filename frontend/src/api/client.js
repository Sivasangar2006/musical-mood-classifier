import axios from 'axios';

// In development: Vite proxy forwards /api/* to localhost:8000
// In production: set VITE_API_URL in your deployment environment
const BASE_URL = import.meta.env.VITE_API_URL || '/api';

const client = axios.create({
    baseURL: BASE_URL,
    timeout: 300000, // 5 minutes — full song analysis can take a while
});

/**
 * Upload an audio file and get back a mood prediction.
 * 
 * @param {File} file - The audio file from the file input
 * @param {function} onProgress - Callback for upload progress (0-100)
 * @returns {Promise<PredictResponse>}
 */
export const predictMood = async (file, onProgress) => {
    // FormData is how browsers send files over HTTP
    // It's like a POST body that can contain binary data alongside text
    const formData = new FormData();
    formData.append('file', file);  // 'file' must match the parameter name in FastAPI

    const response = await client.post('/predict', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',  // Tell the server this is a file upload
        },
        onUploadProgress: (progressEvent) => {
            if (onProgress && progressEvent.total) {
                const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                onProgress(percent);
            }
        },
    });

    return response.data;
};

/**
 * Fetch the prediction history from the database.
 * 
 * @param {number} limit - How many records to return
 * @returns {Promise<HistoryResponse>}
 */
export const getHistory = async (limit = 20) => {
    const response = await client.get(`/history?limit=${limit}`);
    return response.data;
};

/**
 * Fetch aggregated statistics.
 */
export const getStats = async () => {
    const response = await client.get('/stats');
    return response.data;
};

/**
 * CNN-based mood prediction — returns mood + similar_songs from FAISS.
 */
export const predictMoodCNN = async (file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await client.post('/predict/cnn', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
            if (onProgress && e.total) {
                onProgress(Math.round((e.loaded * 100) / e.total));
            }
        },
    });
    return response.data;
};

/**
 * Check which models are currently loaded on the backend.
 */
export const getCapabilities = async () => {
    try {
        const response = await client.get('/capabilities');
        return response.data;
    } catch {
        return { svm: true, cnn: false, faiss: false };
    }
};

/**
 * Fetch Deezer track recommendations for a mood.
 * @param {string} mood - Happy | Energetic | Angry | Sad | Relaxed
 * @param {number} limit - Number of tracks
 * @param {number} offset - Pagination offset (multiples of limit rotate query variant)
 */
export const getRecommendations = async (mood, limit = 8, offset = 0) => {
    const response = await client.get(`/recommendations/${mood}`, {
        params: { limit, offset },
    });
    return response.data;
};

/**
 * Search Deezer for any song/artist name.
 * @param {string} mood - Current mood context
 * @param {string} q - Search query (song name, artist, etc.)
 */
export const searchTracks = async (mood, q, limit = 8) => {
    const response = await client.get(`/recommendations/${mood}/search`, {
        params: { q, limit },
    });
    return response.data;
};

// ─── CLAP valence/arousal engine (the redesign) ──────────────────────────────

/**
 * Search iTunes for any song to analyse (mood-agnostic).
 * @param {string} q - song or artist name
 */
export const searchSongs = async (q, limit = 10) => {
    const response = await client.get(`/recommendations/Happy/search`, {
        params: { q, limit },
    });
    return response.data.tracks;
};

/**
 * Analyse an iTunes track by its 30s preview with the CLAP V/A engine.
 * Returns valence/arousal, mood, quadrant, confidence and similar corpus songs.
 * @param {object} track - { preview_url, title, artist, ... }
 */
export const analyzeTrack = async (track) => {
    const response = await client.post('/analyze/track', {
        preview_url: track.preview_url,
        title: track.title,
        artist: track.artist,
    });
    return response.data;
};

/**
 * Analyse an uploaded audio file with the CLAP V/A engine.
 */
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

/**
 * Model-based mood recommendations from the CLAP corpus (nearest in V/A space).
 * @param {string} mood - Happy | Energetic | Angry | Sad | Relaxed
 */
export const getVARecommendations = async (mood, k = 15) => {
    const response = await client.get(`/va/recommend/${mood}`, { params: { k } });
    return response.data;
};

/**
 * Cross-modal text-to-mood search. Describe a vibe in words; get songs that sound
 * like it via CLAP's shared audio/text space.
 * @param {string} q - free-text vibe, e.g. "rainy sunday morning"
 */
export const searchByVibe = async (q, k = 12) => {
    const response = await client.get('/va/search', { params: { q, k } });
    return response.data;
};

/**
 * Submit human feedback on an analysis (confirm or correct). Feeds continual learning.
 * @param {number} analysisId
 * @param {{correct:boolean, corrected_mood?:string}} body
 */
export const submitVAFeedback = async (analysisId, body) => {
    const response = await client.post(`/va/feedback/${analysisId}`, body);
    return response.data;
};

/** Feedback dashboard stats (how much the model is learning). */
export const getFeedbackStats = async () => {
    const response = await client.get('/va/feedback/stats');
    return response.data;
};

/** Recent analyses with their feedback status (the active History replacement). */
export const getVAHistory = async (limit = 20) => {
    const response = await client.get('/va/history', { params: { limit } });
    return response.data;
};

/** Model evaluation metrics for the "About the model" dashboard. */
export const getMetrics = async () => {
    const response = await client.get('/va/metrics');
    return response.data;
};
