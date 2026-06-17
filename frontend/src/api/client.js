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
