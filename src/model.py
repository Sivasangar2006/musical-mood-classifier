"""
model.py
--------
Loads features.csv, trains SVM + XGBoost classifiers,
evaluates with cross-validation, saves the best model.
"""

import os
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.svm              import SVC
from sklearn.ensemble         import RandomForestClassifier
from sklearn.preprocessing    import StandardScaler, LabelEncoder
from sklearn.model_selection  import (train_test_split,
                                       StratifiedKFold,
                                       cross_val_score,
                                       GridSearchCV)
from sklearn.metrics          import (classification_report,
                                       ConfusionMatrixDisplay,
                                       roc_auc_score)
from sklearn.preprocessing    import label_binarize
from sklearn.pipeline         import Pipeline
import xgboost as xgb

# ─── Config ──────────────────────────────────────────────────────────────────
CSV_PATH    = os.path.join("..", "data", "features.csv")
MODELS_DIR  = os.path.join("..", "models")
PLOTS_DIR   = os.path.join("..", "plots")
RANDOM_SEED = 42

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(PLOTS_DIR,  exist_ok=True)


# ─── Load Data ───────────────────────────────────────────────────────────────
def load_data(csv_path: str):
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} samples, {df['mood'].nunique()} mood classes")
    print(df["mood"].value_counts().to_string())

    meta_cols = ["filename", "genre", "mood"]
    feat_cols = [c for c in df.columns if c not in meta_cols]

    X = df[feat_cols].values.astype(np.float32)
    le = LabelEncoder()
    y = le.fit_transform(df["mood"])

    return X, y, le, feat_cols, df


# ─── Plot: Confusion Matrix ───────────────────────────────────────────────────
def plot_confusion_matrix(model, X_test, y_test, class_names, name):
    fig, ax = plt.subplots(figsize=(7, 6))
    ConfusionMatrixDisplay.from_estimator(
        model, X_test, y_test,
        display_labels=class_names,
        cmap="Blues", ax=ax
    )
    ax.set_title(f"Confusion Matrix — {name}", fontsize=13)
    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, f"confusion_{name.lower().replace(' ','_')}.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"   Saved → {path}")


# ─── Plot: Feature Importance ─────────────────────────────────────────────────
def plot_feature_importance(model, feat_cols, name, top_n=20):
    importances = model.feature_importances_
    df_imp = pd.DataFrame({"feature": feat_cols, "importance": importances})
    df_imp = df_imp.sort_values("importance", ascending=False).head(top_n)

    fig, ax = plt.subplots(figsize=(9, 6))
    sns.barplot(data=df_imp, x="importance", y="feature", color="steelblue", ax=ax)
    ax.set_title(f"Top {top_n} Feature Importances — {name}", fontsize=13)
    ax.set_xlabel("Importance score")
    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, f"feat_importance_{name.lower().replace(' ','_')}.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"   Saved → {path}")


# ─── Train & Evaluate ─────────────────────────────────────────────────────────
def train_and_evaluate(X_train, X_test, y_train, y_test,
                        scaler, le, feat_cols):

    X_tr = scaler.transform(X_train)
    X_te = scaler.transform(X_test)
    classes = le.classes_
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)

    results = {}

    # ── 1. SVM ──────────────────────────────────────────────────────────────
    print("\n[1/3] Training SVM ...")
    svm_pipe = Pipeline([("svm", SVC(kernel="rbf", probability=True,
                                      random_state=RANDOM_SEED))])
    param_grid = {
        "svm__C":     [0.1, 1, 10, 100],
        "svm__gamma": ["scale", "auto", 0.001, 0.01],
    }
    svm_gs = GridSearchCV(svm_pipe, param_grid, cv=cv,
                           scoring="f1_macro", n_jobs=-1, verbose=0)
    svm_gs.fit(X_tr, y_train)
    svm_best = svm_gs.best_estimator_

    svm_pred = svm_best.predict(X_te)
    print(f"   Best params : {svm_gs.best_params_}")
    print(f"   CV F1-macro : {svm_gs.best_score_:.3f}")
    print(f"   Test report :\n{classification_report(y_test, svm_pred, target_names=classes)}")
    plot_confusion_matrix(svm_best, X_te, y_test, classes, "SVM")
    results["SVM"] = svm_gs.best_score_

    # ── 2. Random Forest ────────────────────────────────────────────────────
    print("\n[2/3] Training Random Forest ...")
    rf = RandomForestClassifier(n_estimators=300, max_depth=None,
                                 n_jobs=-1, random_state=RANDOM_SEED)
    rf_cv = cross_val_score(rf, X_tr, y_train, cv=cv,
                             scoring="f1_macro", n_jobs=-1)
    rf.fit(X_tr, y_train)
    rf_pred = rf.predict(X_te)
    print(f"   CV F1-macro : {rf_cv.mean():.3f} ± {rf_cv.std():.3f}")
    print(f"   Test report :\n{classification_report(y_test, rf_pred, target_names=classes)}")
    plot_confusion_matrix(rf, X_te, y_test, classes, "Random Forest")
    plot_feature_importance(rf, feat_cols, "Random Forest")
    results["Random Forest"] = rf_cv.mean()

    # ── 3. XGBoost ──────────────────────────────────────────────────────────
    print("\n[3/3] Training XGBoost ...")
    xgb_model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    xgb_cv = cross_val_score(xgb_model, X_tr, y_train, cv=cv,
                              scoring="f1_macro", n_jobs=-1)
    xgb_model.fit(X_tr, y_train,
                  eval_set=[(X_te, y_test)],
                  verbose=False)
    xgb_pred = xgb_model.predict(X_te)
    print(f"   CV F1-macro : {xgb_cv.mean():.3f} ± {xgb_cv.std():.3f}")
    print(f"   Test report :\n{classification_report(y_test, xgb_pred, target_names=classes)}")
    plot_confusion_matrix(xgb_model, X_te, y_test, classes, "XGBoost")
    plot_feature_importance(xgb_model, feat_cols, "XGBoost")
    results["XGBoost"] = xgb_cv.mean()

    # ── AUC (XGBoost) ────────────────────────────────────────────────────────
    y_test_bin = label_binarize(y_test, classes=list(range(len(classes))))
    y_proba    = xgb_model.predict_proba(X_te)
    auc = roc_auc_score(y_test_bin, y_proba, multi_class="ovr", average="macro")
    print(f"\n   XGBoost Macro AUC : {auc:.3f}")

    return svm_best, rf, xgb_model, results


# ─── Save Best Model ──────────────────────────────────────────────────────────
def save_model(model, scaler, le, results):
    best_name = max(results, key=results.get)
    model_map = {"SVM": model[0], "Random Forest": model[1], "XGBoost": model[2]}
    best_model = model_map[best_name]

    joblib.dump(best_model, os.path.join(MODELS_DIR, "model.pkl"))
    joblib.dump(scaler,     os.path.join(MODELS_DIR, "scaler.pkl"))
    joblib.dump(le,         os.path.join(MODELS_DIR, "encoder.pkl"))

    print(f"\n✅ Best model : {best_name} (CV F1 = {results[best_name]:.3f})")
    print(f"   Saved to   : {MODELS_DIR}/")


# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  MOOD CLASSIFIER — MODEL TRAINING")
    print("=" * 55)

    X, y, le, feat_cols, df = load_data(CSV_PATH)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=RANDOM_SEED
    )

    scaler = StandardScaler()
    scaler.fit(X_train)   # fit ONLY on train — never on test

    svm_m, rf_m, xgb_m, results = train_and_evaluate(
        X_train, X_test, y_train, y_test, scaler, le, feat_cols
    )

    save_model((svm_m, rf_m, xgb_m), scaler, le, results)

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n── Model Comparison ──────────────────────────")
    for name, score in sorted(results.items(), key=lambda x: -x[1]):
        bar = "█" * int(score * 40)
        print(f"  {name:<15} {score:.3f}  {bar}")
    print("─" * 46)


if __name__ == "__main__":
    main()
