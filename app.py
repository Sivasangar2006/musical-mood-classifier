"""
app.py
------
Streamlit demo — upload a .wav/.mp3 and get mood prediction.
Run with: streamlit run app.py
"""

import streamlit as st
import numpy as np
import joblib
import os
import sys
import tempfile

sys.path.append("src")
from extract import extract_features

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Music Mood Classifier",
    page_icon="🎵",
    layout="centered",
)

MOOD_EMOJI = {
    "Happy":     "😊",
    "Sad":       "😢",
    "Angry":     "😠",
    "Relaxed":   "😌",
    "Energetic": "⚡",
}

MOOD_COLOR = {
    "Happy":     "#F4C430",
    "Sad":       "#4682B4",
    "Angry":     "#DC143C",
    "Relaxed":   "#3CB371",
    "Energetic": "#FF8C00",
}

MOOD_DESC = {
    "Happy":     "High valence, high arousal — bright, upbeat, positive energy.",
    "Sad":       "Low valence, low arousal — melancholic, slow, introspective.",
    "Angry":     "Low valence, high arousal — intense, aggressive, heavy.",
    "Relaxed":   "High valence, low arousal — calm, soothing, peaceful.",
    "Energetic": "High arousal — fast, driving, full of energy.",
}


# ─── Load Model ──────────────────────────────────────────────────────────────
@st.cache_resource
def load_model():
    models_dir = "models"
    try:
        model   = joblib.load(os.path.join(models_dir, "model.pkl"))
        scaler  = joblib.load(os.path.join(models_dir, "scaler.pkl"))
        encoder = joblib.load(os.path.join(models_dir, "encoder.pkl"))
        return model, scaler, encoder
    except FileNotFoundError:
        return None, None, None


# ─── UI ──────────────────────────────────────────────────────────────────────
st.title("🎵 Musical Mood Classifier")
st.markdown(
    "Upload a song clip and the model will predict its **emotional mood** "
    "using audio features (MFCCs, chroma, tempo, spectral features)."
)
st.markdown("---")

model, scaler, encoder = load_model()

if model is None:
    st.error(
        "⚠️  Model not found. Run `python src/model.py` first to train "
        "and save the model, then restart this app."
    )
    st.stop()

# ─── Upload ──────────────────────────────────────────────────────────────────
audio_file = st.file_uploader(
    "Upload a .wav or .mp3 file (30 seconds works best)",
    type=["wav", "mp3"],
)

if audio_file is not None:
    st.audio(audio_file, format="audio/wav")

    with st.spinner("Extracting audio features..."):
        # write to temp file so librosa can read it
        suffix = ".wav" if audio_file.name.endswith(".wav") else ".mp3"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_file.read())
            tmp_path = tmp.name

        try:
            feats = extract_features(tmp_path).reshape(1, -1)
            feats_scaled = scaler.transform(feats)
            proba = model.predict_proba(feats_scaled)[0]
            pred_idx  = np.argmax(proba)
            pred_mood = encoder.classes_[pred_idx]
            confidence = proba[pred_idx]
        except Exception as e:
            st.error(f"Feature extraction failed: {e}")
            st.stop()
        finally:
            os.unlink(tmp_path)

    # ── Result ───────────────────────────────────────────────────────────────
    st.markdown("---")
    emoji = MOOD_EMOJI.get(pred_mood, "🎵")
    color = MOOD_COLOR.get(pred_mood, "#888")

    st.markdown(
        f"<h2 style='text-align:center; color:{color};'>"
        f"{emoji} {pred_mood}"
        f"</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='text-align:center; color:gray;'>"
        f"{MOOD_DESC.get(pred_mood, '')}</p>",
        unsafe_allow_html=True,
    )

    st.markdown(f"**Confidence:** {confidence:.1%}")
    st.progress(float(confidence))

    # ── All class probabilities ───────────────────────────────────────────
    st.markdown("#### All mood probabilities")
    sorted_probs = sorted(zip(encoder.classes_, proba), key=lambda x: -x[1])

    for mood, prob in sorted_probs:
        col1, col2, col3 = st.columns([2, 6, 1])
        with col1:
            st.write(f"{MOOD_EMOJI.get(mood, '')} {mood}")
        with col2:
            st.progress(float(prob))
        with col3:
            st.write(f"{prob:.1%}")

    # ── Russell's Model placement ─────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📍 Russell's Circumplex Model")
    QUADRANT = {
        "Happy":     "🟡 **Positive Valence + High Arousal** (top-right)",
        "Sad":       "🔵 **Negative Valence + Low Arousal** (bottom-left)",
        "Angry":     "🔴 **Negative Valence + High Arousal** (top-left)",
        "Relaxed":   "🟢 **Positive Valence + Low Arousal** (bottom-right)",
        "Energetic": "🟠 **High Arousal** (top region)",
    }
    st.markdown(QUADRANT.get(pred_mood, ""))

# ─── Sidebar info ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### About")
    st.markdown(
        "**Musical Mood Classification Engine**\n\n"
        "Built using:\n"
        "- `librosa` for audio feature extraction\n"
        "- MFCCs, Chroma, Tempo, Spectral features\n"
        "- GTZAN dataset (1000 songs, 10 genres)\n"
        "- SVM / XGBoost classifier\n\n"
        "Mood taxonomy based on **Russell's Circumplex Model of Affect** (1980)."
    )
    st.markdown("---")
    st.markdown("### Features extracted")
    st.markdown(
        "- 13 MFCC means + 13 stds\n"
        "- 12 Chroma means\n"
        "- Spectral centroid, rolloff, bandwidth\n"
        "- Spectral contrast (7)\n"
        "- Zero Crossing Rate\n"
        "- RMS Energy\n"
        "- Tempo (BPM)\n\n"
        "**Total: 56 features per song**"
    )
