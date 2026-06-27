# MoodWave — single-container build for Hugging Face Spaces (Docker SDK).
# Stage 1 builds the React frontend; stage 2 runs FastAPI and serves both the
# API and the built frontend on port 7860 (the port HF Spaces expects).

# ---- Stage 1: build the frontend ----
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
# Same-origin deploy: empty VITE_API_URL -> the SPA calls the Space's own origin.
# VITE_GOOGLE_CLIENT_ID is the public OAuth client id (safe to bake); override at
# build time with --build-arg if you ever rotate it.
ARG VITE_GOOGLE_CLIENT_ID=264881129943-531ph3cp87b1img02ivjqf7659dk0d0r.apps.googleusercontent.com
RUN printf 'VITE_API_URL=\nVITE_GOOGLE_CLIENT_ID=%s\n' "$VITE_GOOGLE_CLIENT_ID" > .env.production
RUN npm run build

# ---- Stage 2: Python runtime ----
FROM python:3.11-slim
WORKDIR /app

# libsndfile1 is required by librosa/soundfile; PyAV bundles its own ffmpeg.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libsndfile1 \
 && rm -rf /var/lib/apt/lists/*

# Cache HF model weights in a writable, baked-in location.
ENV HF_HOME=/app/.cache/huggingface
ENV PYTHONUNBUFFERED=1

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Bake the CLAP weights into the image so cold starts don't re-download ~600 MB.
RUN python -c "from transformers import ClapModel, ClapProcessor; \
ClapModel.from_pretrained('laion/clap-htsat-unfused'); \
ClapProcessor.from_pretrained('laion/clap-htsat-unfused')"

# App code + model artifacts (paths resolve relative to /app — see predict_va.py).
COPY backend/ ./backend/
COPY src/ ./src/
COPY artifacts/ ./artifacts/

# Built frontend → served by FastAPI from backend/static.
COPY --from=frontend /fe/dist ./backend/static

EXPOSE 7860
WORKDIR /app/backend
CMD ["gunicorn", "main:app", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:7860", "--timeout", "180"]
