/**
 * Last.fm API client for mood-based song recommendations.
 * Get a free API key at https://www.last.fm/api/account/create
 * Set VITE_LASTFM_API_KEY in your .env file.
 */

const API_KEY  = import.meta.env.VITE_LASTFM_API_KEY || '';
const BASE_URL = 'https://ws.audioscrobbler.com/2.0/';

// Map our moods to Last.fm tags that yield good results
const MOOD_TAGS = {
  Happy:     ['happy', 'feel-good', 'upbeat'],
  Energetic: ['energetic', 'workout', 'party'],
  Angry:     ['aggressive', 'heavy', 'metal'],
  Sad:       ['sad', 'melancholy', 'emotional'],
  Relaxed:   ['chill', 'relaxing', 'ambient'],
};

/**
 * Fetch top tracks for a mood tag.
 * @param {string} mood - One of Happy/Energetic/Angry/Sad/Relaxed
 * @param {number} limit - Number of tracks to fetch
 * @returns {Promise<Array>} Array of track objects
 */
export const getTracksForMood = async (mood, limit = 8) => {
  if (!API_KEY) return [];

  const tags  = MOOD_TAGS[mood] || ['pop'];
  const tag   = tags[Math.floor(Math.random() * tags.length)];
  const page  = 1;

  const params = new URLSearchParams({
    method:  'tag.getTopTracks',
    tag,
    api_key: API_KEY,
    format:  'json',
    limit:   String(limit),
    page:    String(page),
  });

  const res  = await fetch(`${BASE_URL}?${params}`);
  const data = await res.json();
  const raw  = data?.tracks?.track ?? [];

  return raw.map((t) => ({
    name:    t.name,
    artist:  t.artist?.name ?? 'Unknown',
    url:     t.url,
    image:   t.image?.find((i) => i.size === 'medium')?.['#text'] || null,
  }));
};
