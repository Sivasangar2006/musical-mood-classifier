"""
Mood Classification — Train & Evaluate
Standalone script equivalent of notebooks/03_model.ipynb.

Usage:
    python src/model.py                         # defaults to data/features.csv
    python src/model.py --csv path/to/file.csv  # custom path
"""
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import joblib
from pathlib import Path

from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, ConfusionMatrixDisplay
import xgboost as xgb


def load_data(csv_path: str) -> pd.DataFrame:
    """Load features CSV and print summary."""
    df = pd.read_csv(csv_path)
    print(f"[OK] Loaded {len(df)} tracks, {df.shape[1]} columns from {csv_path}")
    print(f"  Mood distribution:\n{df['mood'].value_counts().to_string()}\n")
    return df


def prepare_data(df: pd.DataFrame):
    """Split features/labels, encode, scale, and return train/test sets."""
    feat_cols = [c for c in df.columns if c not in ['filename', 'genre', 'mood']]
    X = df[feat_cols].values

    le = LabelEncoder()
    y = le.fit_transform(df['mood'])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    return X_train, X_test, y_train, y_test, le, scaler


def train_svm(X_train, y_train):
    """Train an RBF-kernel SVM."""
    model = SVC(kernel='rbf', C=10, probability=True, random_state=42)
    model.fit(X_train, y_train)
    return model


def train_xgboost(X_train, y_train):
    """Train an XGBoost classifier."""
    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=5,
        use_label_encoder=False,
        eval_metric='mlogloss',
        random_state=42,
    )
    model.fit(X_train, y_train)
    return model


def train_rf(X_train, y_train):
    """Train a Random Forest classifier."""
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        random_state=42,
    )
    model.fit(X_train, y_train)
    return model


def evaluate(model, name, X_test, y_test, le):
    """Print classification report for a model."""
    preds = model.predict(X_test)
    print(f"{'=' * 50}")
    print(f"  {name}")
    print(f"{'=' * 50}")
    print(classification_report(y_test, preds, target_names=le.classes_))


def plot_confusion(model, name, X_test, y_test, le, save_dir):
    """Plot and save confusion matrix."""
    fig, ax = plt.subplots(figsize=(7, 6))
    ConfusionMatrixDisplay.from_estimator(
        model, X_test, y_test, display_labels=le.classes_, ax=ax, cmap='Blues'
    )
    ax.set_title(f'{name} — Confusion Matrix')
    plt.tight_layout()
    path = save_dir / f'confusion_{name.lower().replace(" ", "_")}.png'
    fig.savefig(path, dpi=150)
    print(f"  Saved -> {path}")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Train mood classifiers")
    parser.add_argument('--csv', default='data/features.csv', help='Path to features CSV')
    args = parser.parse_args()

    # Directories
    out_dir = Path('models')
    out_dir.mkdir(exist_ok=True)
    fig_dir = Path('figures')
    fig_dir.mkdir(exist_ok=True)

    # Load & prepare
    df = load_data(args.csv)
    X_train, X_test, y_train, y_test, le, scaler = prepare_data(df)

    # Train all three models
    models = {
        'SVM': train_svm(X_train, y_train),
        'XGBoost': train_xgboost(X_train, y_train),
        'Random Forest': train_rf(X_train, y_train),
    }

    # Evaluate & plot
    for name, model in models.items():
        evaluate(model, name, X_test, y_test, le)
        plot_confusion(model, name, X_test, y_test, le, fig_dir)

    # Save best model (XGBoost) + scaler + encoder
    joblib.dump(models['XGBoost'], out_dir / 'xgb_mood.pkl')
    joblib.dump(scaler, out_dir / 'scaler.pkl')
    joblib.dump(le, out_dir / 'label_encoder.pkl')
    print(f"\n[OK] Saved XGBoost model, scaler, and label encoder to {out_dir}/")


if __name__ == '__main__':
    main()
