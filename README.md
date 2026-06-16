# Musical Mood Classifier

A full-stack machine learning web application that listens to a song and tells you its emotional mood — Happy, Sad, Energetic, Angry, or Relaxed.

**Live Demo:** https://musical-mood-classifier.vercel.app  
**Backend API:** https://musical-mood-classifier.onrender.com

---

## Table of Contents

1. [What This Project Does](#1-what-this-project-does)
2. [Why I Built This](#2-why-i-built-this)
3. [Dataset](#3-dataset)
4. [Genre to Mood Mapping](#4-genre-to-mood-mapping)
5. [Feature Extraction](#5-feature-extraction)
6. [Model Training](#6-model-training)
7. [Results](#7-results)
8. [System Architecture](#8-system-architecture)
9. [Tech Stack](#9-tech-stack)
10. [How to Run Locally](#10-how-to-run-locally)
11. [Challenges and Learnings](#11-challenges-and-learnings)

---

## 1. What This Project Does

You upload any `.wav` or `.mp3` file. The system:

1. Extracts **56 numerical audio features** from the file using signal processing
2. Feeds those numbers into a trained machine learning model
3. Returns the predicted mood along with a confidence percentage and a breakdown of probabilities for all 5 moods
4. Saves the prediction to a PostgreSQL database so you can view your history

No genre detection. No lyrics analysis. The model purely reads the sound wave — tempo, tone, energy, rhythm — and maps it to a human emotion.

---

## 2. Why I Built This

Music streaming platforms like Spotify use mood-based playlists ("Chill Vibes", "Workout Bangers") but they rely on manual tagging or complex proprietary systems. I wanted to understand: **can a simple ML model classify mood just from audio signals?**

This project answers that question end-to-end — from raw audio files all the way to a deployed web app that anyone can use.

---

## 3. Dataset

### What is GTZAN?

I used the **GTZAN Genre Collection**, one of the most well-known publicly available datasets in Music Information Retrieval (MIR) research. It was originally created by George Tzanetakis and Perry Cook.

**Dataset facts:**
- **1,000 audio clips** total (999 usable after one corrupted file)
- **10 music genres:** blues, classical, country, disco, hiphop, jazz, metal, pop, reggae, rock
- **100 songs per genre** (except jazz which has 99)
- Each clip is exactly **30 seconds long**
- All files are `.wav` format, **22,050 Hz** sample rate, **mono** channel

### Why 30 seconds?

30 seconds is long enough to capture the overall character of a song (tempo, tonal patterns, energy) but short enough to keep feature extraction fast. We only load the first 30 seconds of any uploaded file too — so the API response stays under a few seconds.

### Class Distribution After Mapping

| Mood | Count | Source Genres |
|------|-------|---------------|
| Happy | 300 | pop, disco, reggae |
| Sad | 200 | blues, country |
| Energetic | 200 | hiphop, rock |
| Relaxed | 199 | classical, jazz |
| Angry | 100 | metal |

Notice that **Angry is underrepresented** (100 vs 300 for Happy). This caused the model to incorrectly classify aggressive music like death metal as Happy. I fixed this by training with **balanced class weights** — which penalizes mistakes on minority classes more heavily.

---

## 4. Genre to Mood Mapping

GTZAN gives us **genre labels** but we want **mood labels**. I created a mapping based on how each genre is commonly perceived emotionally:

```
pop      → Happy       (upbeat, positive energy)
disco    → Happy       (danceable, feel-good)
reggae   → Happy       (laid-back but joyful)

hiphop   → Energetic   (rhythmic, driving beats)
rock     → Energetic   (loud, powerful, forward-moving)

metal    → Angry       (aggressive, intense, heavy)

blues    → Sad         (melancholic, slow, introspective)
country  → Sad         (storytelling, often about loss)

classical→ Relaxed     (structured, calming, no lyrics)
jazz     → Relaxed     (smooth, improvisational, chill)
```

This mapping is a simplification. Real emotions in music are complex and subjective — but for a supervised learning problem, we need clean labels, and these generalizations hold well enough across 1,000 songs.

---

## 5. Feature Extraction

This is the most technically important part. We cannot feed raw audio waveforms into a traditional ML model — a 30-second `.wav` file has **661,500 data points** (22,050 samples/sec × 30 sec). Instead, we summarize the audio into **56 meaningful numbers**.

All feature extraction uses **librosa**, a Python library for audio analysis.

### The 56 Features

#### 1. MFCCs — Mel-Frequency Cepstral Coefficients (26 features)
**What they are:** MFCCs describe the shape of the sound spectrum in a way that mimics how human ears perceive sound. The "mel" scale is a perceptual scale of pitches — equal distances on this scale correspond to equal perceived pitch differences.

**How we use them:** We extract 13 MFCC coefficients. For each coefficient, we compute:
- The **mean** across the entire 30 seconds → 13 numbers
- The **standard deviation** across the 30 seconds → 13 numbers

This gives us 26 features. The mean captures the overall tonal character; the std captures how much the tone varies over time (a steady classical piece vs. a dynamic rock song will differ here).

**Why MFCCs matter for mood:** Happy, upbeat music tends to have higher, brighter frequency content. Sad or relaxed music tends to be darker and lower. MFCCs capture this.

#### 2. Chroma Features (12 features)
**What they are:** Chroma features represent the energy present in each of the 12 pitch classes (C, C#, D, D#, E, F, F#, G, G#, A, A#, B) of the Western musical scale.

**How we use them:** Mean of each chroma bin across the song → 12 numbers.

**Why they matter:** Major keys (lots of energy in certain chroma bins) tend to feel happier. Minor keys feel sadder. This is directly captured here.

#### 3. Spectral Centroid (2 features)
**What it is:** The "center of mass" of the frequency spectrum. A song with mostly high-frequency content (bright, sharp) will have a high centroid. A song with mostly low-frequency content (bass, dark) will have a low centroid.

**How we use it:** Mean and standard deviation → 2 numbers.

**Why it matters:** Energetic and happy music tends to be brighter (higher centroid). Sad and relaxed music tends to be darker (lower centroid).

#### 4. Spectral Rolloff (2 features)
**What it is:** The frequency below which 85% of the total spectral energy is contained. Think of it as the "brightness cutoff" — it tells you where the meaningful frequency content ends.

**How we use it:** Mean and standard deviation → 2 numbers.

#### 5. Spectral Bandwidth (2 features)
**What it is:** How wide or narrow the frequency spread is around the spectral centroid. A song with both deep bass and high treble will have high bandwidth. A mellow, mid-focused song will have low bandwidth.

**How we use it:** Mean and standard deviation → 2 numbers.

#### 6. Spectral Contrast (7 features)
**What it is:** The difference between peaks (loud frequencies) and valleys (quiet frequencies) in different frequency bands. High contrast means the song has strong, defined musical notes. Low contrast means a more noise-like texture.

**How we use it:** Mean across 7 frequency sub-bands → 7 numbers.

**Why it matters:** Metal and rock have very high spectral contrast (crunchy, defined guitar riffs). Classical can vary — orchestral pieces have high contrast, ambient pieces have low.

#### 7. Zero Crossing Rate — ZCR (2 features)
**What it is:** How many times per second the audio waveform crosses zero (flips from positive to negative). Noisy, percussive signals cross zero very frequently. Pure tones cross zero rarely.

**How we use it:** Mean and standard deviation → 2 numbers.

**Why it matters:** Metal and rock have high ZCR (distorted guitars cross zero constantly). Classical and jazz have low ZCR (smooth, tonal sounds).

#### 8. RMS Energy (2 features)
**What it is:** Root Mean Square energy — the average loudness/power of the audio signal. High RMS means loud and energetic. Low RMS means quiet and calm.

**How we use it:** Mean and standard deviation → 2 numbers.

**Why it matters:** This is the most direct measure of intensity. Angry and Energetic songs have high RMS. Relaxed songs have low RMS.

#### 9. Tempo (1 feature)
**What it is:** The estimated beats per minute (BPM) of the song, extracted by librosa's beat tracking algorithm.

**How we use it:** Single number → 1 feature.

**Why it matters:** Happy and Energetic songs tend to be fast (120–180 BPM). Sad and Relaxed songs tend to be slow (60–100 BPM). Angry metal is often very fast (150–220 BPM).

### Feature Vector Summary

| Feature Group | Count | What It Captures |
|---|---|---|
| MFCC means | 13 | Overall tonal texture |
| MFCC stds | 13 | Tonal variation over time |
| Chroma means | 12 | Pitch class energy (key/harmony) |
| Spectral centroid | 2 | Brightness |
| Spectral rolloff | 2 | Brightness cutoff |
| Spectral bandwidth | 2 | Frequency spread |
| Spectral contrast | 7 | Note definition vs. noise |
| ZCR | 2 | Noisiness / percussion |
| RMS energy | 2 | Loudness / intensity |
| Tempo | 1 | Speed |
| **Total** | **56** | |

---

## 6. Model Training

### Training Pipeline

The training code lives in `src/model.py`. Here is what happens step by step:

**Step 1 — Load features.csv**  
All 56 features for all 999 songs are loaded from a pre-built CSV file. The features were extracted once using `src/extract.py` which iterated over the GTZAN audio files.

**Step 2 — Encode labels**  
The mood labels (Happy, Sad, etc.) are strings. We use `sklearn.LabelEncoder` to convert them to integers (0–4). The encoder is saved to `models/encoder.pkl` so predictions can be decoded back to mood names.

**Step 3 — Train/test split**  
We split 80% of data for training and 20% for testing using **stratified splitting** — meaning each split has the same class proportions. This ensures the test set has enough samples of every mood class.

**Step 4 — Feature scaling**  
We apply `StandardScaler` to normalize all features to have mean=0 and std=1. This is critical for SVM — it is sensitive to feature scales (a feature ranging 0–1000 would dominate one ranging 0–1 without scaling). The scaler is fitted **only on training data** and saved to `models/scaler.pkl`. At inference time, new audio is scaled using the same scaler.

**Step 5 — Train three models**

We train and compare three classifiers:

**a) Support Vector Machine (SVM)**  
- Kernel: RBF (Radial Basis Function) — handles non-linear relationships between features
- Hyperparameters tuned via **GridSearchCV**: `C` (margin softness) and `gamma` (kernel width)
- 5-fold cross-validation used for evaluation
- `class_weight="balanced"` to handle class imbalance

**b) Random Forest**  
- 300 decision trees, each trained on a random subset of features and samples
- Predictions are made by majority vote across all trees
- `class_weight="balanced"` applied
- Also gives us **feature importances** — which of the 56 features matter most

**c) XGBoost (Extreme Gradient Boosting)**  
- Builds trees sequentially, each one correcting the errors of the previous
- `sample_weight` calculated from class frequencies to handle imbalance
- Generally the strongest model for tabular data

**Step 6 — Evaluate with 5-fold cross-validation**  
Instead of a single train/test split, we use 5-fold CV: data is split into 5 parts, the model trains on 4 and tests on 1, rotating 5 times. The average F1-macro score across 5 folds is the final performance metric.

**F1-macro** is used (not accuracy) because the classes are imbalanced. Accuracy would look good just by predicting "Happy" more often. F1-macro treats all classes equally.

**Step 7 — Save best model**  
The model with the highest cross-validation F1-macro score is saved to `models/model.pkl`.

---

## 7. Results

### Final Model Performance (SVM — Best Model)

```
              precision    recall  f1-score   support

       Angry       0.75      0.60      0.67        20
   Energetic       0.59      0.68      0.63        40
       Happy       0.85      0.87      0.86        60
     Relaxed       0.97      0.90      0.94        40
         Sad       0.85      0.85      0.85        40

    accuracy                           0.81       200
   macro avg       0.80      0.78      0.79       200
```

### Model Comparison

| Model | CV F1-macro |
|---|---|
| SVM | **0.811** |
| XGBoost | 0.776 |
| Random Forest | 0.769 |

### XGBoost ROC-AUC
`0.961` (macro average, one-vs-rest) — meaning the model can almost perfectly distinguish between moods in terms of ranking.

### What These Numbers Mean

- **Precision:** When the model says "this is Relaxed", it's right 97% of the time
- **Recall:** Of all actual Relaxed songs, the model correctly identifies 90% of them
- **F1-score:** Harmonic mean of precision and recall — the overall quality per class
- **81% accuracy** means 162 out of 200 test songs are classified correctly

The hardest class is **Angry** (recall 0.60) because metal (our Angry training data) shares some acoustic properties with energetic rock. This is expected — the distinction between "angry metal" and "energetic rock" is genuinely subtle in pure audio features.

---

## 8. System Architecture

```
User's Browser
     │
     │  Upload audio file (multipart/form-data)
     ▼
React Frontend (Vercel)
     │
     │  POST /predict  (HTTPS)
     ▼
FastAPI Backend (Render)
     │
     ├── 1. Validate file type (wav/mp3 only)
     ├── 2. Save to /tmp with unique UUID filename
     ├── 3. Extract 56 features using librosa
     ├── 4. Scale features using StandardScaler
     ├── 5. Predict using SVM model
     ├── 6. Save result to PostgreSQL (Neon)
     └── 7. Return JSON response + cleanup temp file
          │
          ▼
     PostgreSQL DB (Neon)
     (stores all predictions for history/stats)
```

### Why Each Technology Was Chosen

**FastAPI** over Flask: FastAPI is async, auto-generates API docs at `/docs`, and uses Pydantic for request/response validation. It's faster and more modern.

**PostgreSQL** over SQLite: SQLite is a file on disk — on Render's free tier, the disk resets on every deploy, wiping all data. PostgreSQL is a real persistent database hosted separately.

**Alembic** for database migrations: lets us evolve the database schema (add columns, rename tables) without losing data.

**Vercel** for frontend: optimized for React/Vite with global CDN, automatic HTTPS, and zero-config deployment.

**Render** for backend: supports persistent servers (unlike serverless functions which would time out during the 2–3 second librosa feature extraction).

---

## 9. Tech Stack

### Machine Learning
| Library | Version | Purpose |
|---|---|---|
| librosa | 0.10.2 | Audio loading and feature extraction |
| scikit-learn | 1.7.2 | SVM, Random Forest, preprocessing |
| XGBoost | 2.0.3 | Gradient boosting classifier |
| numpy | 1.26.4 | Numerical operations |
| pandas | 2.2.2 | Data manipulation |
| joblib | 1.4.2 | Saving/loading model files |
| soundfile | 0.12.1 | Audio file I/O |

### Backend
| Library | Version | Purpose |
|---|---|---|
| FastAPI | 0.111.0 | REST API framework |
| uvicorn | 0.29.0 | ASGI server |
| SQLAlchemy | 2.0.30 | ORM for database access |
| Alembic | 1.13.1 | Database migration tool |
| psycopg2-binary | 2.9.9 | PostgreSQL driver |
| pydantic | 2.7.1 | Data validation |
| python-dotenv | 1.0.1 | Environment variable management |

### Frontend
| Library | Version | Purpose |
|---|---|---|
| React | 19 | UI framework |
| Vite | 8 | Build tool and dev server |
| Tailwind CSS | 3 | Utility-first styling |
| Axios | 1 | HTTP client for API calls |
| Lucide React | latest | Icons |

### Infrastructure
| Service | Purpose |
|---|---|
| GitHub | Version control |
| Render | Backend hosting (FastAPI) |
| Vercel | Frontend hosting (React) |
| Neon | Managed PostgreSQL database |

---

## 10. How to Run Locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL running locally (or a Neon/Supabase free account)

### 1. Clone the repository
```bash
git clone https://github.com/Sivasangar2006/musical-mood-classifier.git
cd musical-mood-classifier
```

### 2. Set up the backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
```

Create `backend/.env`:
```
DATABASE_URL=postgresql://localhost/moodclassifier
MODEL_DIR=../models
```

Run the server:
```bash
uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 3. Set up the frontend
```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: http://localhost:5173

### 4. (Optional) Retrain the model

Download the GTZAN dataset and place it at `data/raw/Data/genres_original/`, then:
```bash
cd src
python extract.py   # extracts features into data/features.csv
python model.py     # trains models and saves to models/
```

---

## 11. Challenges and Learnings

### Class Imbalance
The biggest accuracy problem was that `Angry` had only 100 training samples while `Happy` had 300. The model was biased toward predicting Happy. Fixed by adding `class_weight="balanced"` to all three models, which automatically adjusts the loss function to penalize mistakes on minority classes proportionally more.

### scikit-learn Version Mismatch
The `.pkl` model files are serialized with the exact scikit-learn version used to train them. Trying to load a model saved with sklearn 1.7.2 in an environment running 1.4.2 throws warnings and can cause failures. Always pin the sklearn version in `requirements.txt` to match the version used for training.

### CORS in Production
The browser blocks cross-origin requests by default. The frontend on `vercel.app` calling the backend on `onrender.com` are different origins. Configuring FastAPI's `CORSMiddleware` to explicitly allow the frontend's domain was required.

### Render and PostgreSQL
Render doesn't allow `apt-get` in the build step. Most Python packages that need system libraries bundle them in their wheels — `soundfile` bundles `libsndfile`, so no system install is needed. Also, Render provides PostgreSQL URLs starting with `postgres://` but SQLAlchemy requires `postgresql://` — a one-line string replacement handles this.

### Audio Feature Limitations
Pure acoustic features (MFCCs, spectral, rhythm) cannot capture everything a human hears. Death metal and upbeat pop can share similar tempo and energy characteristics. A more accurate system would incorporate genre recognition, lyric sentiment analysis, or a deep learning model trained directly on spectrograms — all of which are extensions worth exploring.

---

## Project Structure

```
musical-mood-classifier/
│
├── data/
│   └── features.csv          # Pre-extracted features for all 999 songs
│
├── models/
│   ├── model.pkl             # Trained SVM classifier
│   ├── scaler.pkl            # Fitted StandardScaler
│   └── encoder.pkl           # LabelEncoder (mood name ↔ integer)
│
├── src/
│   ├── extract.py            # Feature extraction from audio files
│   ├── model.py              # Model training pipeline
│   └── predict.py            # Standalone prediction script
│
├── backend/
│   ├── main.py               # FastAPI application + API endpoints
│   ├── database.py           # SQLAlchemy engine + session setup
│   ├── models.py             # Database table definitions
│   ├── schemas.py            # Pydantic request/response schemas
│   ├── requirements.txt      # Python dependencies
│   └── Procfile              # Render start command
│
├── frontend/
│   ├── src/
│   │   ├── api/client.js     # Axios API client
│   │   └── components/       # React UI components
│   ├── public/
│   │   └── demo-song.mp3     # Demo track for the landing page
│   └── package.json
│
├── notebooks/
│   ├── 01_eda.ipynb          # Exploratory data analysis
│   ├── 02_features.ipynb     # Feature engineering exploration
│   └── 03_model.ipynb        # Model experimentation
│
└── .python-version           # Pins Python 3.11.9 for Render
```

---

## API Reference

### `POST /predict`
Upload an audio file and get a mood prediction.

**Request:** `multipart/form-data` with field `file` (wav or mp3)

**Response:**
```json
{
  "mood": "Energetic",
  "confidence": 0.87,
  "probabilities": {
    "Angry": 0.03,
    "Energetic": 0.87,
    "Happy": 0.05,
    "Relaxed": 0.02,
    "Sad": 0.03
  },
  "mood_emoji": "⚡",
  "mood_description": "Fast, driving, full of energy",
  "prediction_id": 42
}
```

### `GET /history?limit=20`
Returns the last N predictions stored in the database.

### `GET /stats`
Returns mood distribution across all predictions.

### `GET /`
Health check — returns `{"status": "ok"}`.
