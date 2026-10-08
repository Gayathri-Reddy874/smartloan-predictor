"""Train and evaluate the optional approval-probability model.

    python train_model.py --data data/train.csv

Expects the public "Loan Prediction" dataset (Loan_Status = Y/N). Writes
models/loan_model.joblib and models/loan_model.metrics.json.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import ml


def candidates(seed: int) -> dict[str, Pipeline]:
    return {
        "logistic_regression": Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]),
        "random_forest": Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("clf", RandomForestClassifier(n_estimators=300, min_samples_leaf=5,
                                           class_weight="balanced", random_state=seed)),
        ]),
    }


def main(argv=None) -> dict:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", required=True, help="Path to the Loan Prediction CSV")
    p.add_argument("--out", default="models/loan_model.joblib")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)

    X, y = ml.prepare_training_frame(pd.read_csv(args.data))
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=args.seed)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=args.seed)
    cv_auc = {name: float(cross_val_score(pipe, X_tr, y_tr, cv=cv, scoring="roc_auc").mean())
              for name, pipe in candidates(args.seed).items()}
    best = max(cv_auc, key=cv_auc.get)
    pipe = candidates(args.seed)[best].fit(X_tr, y_tr)

    pred, proba = pipe.predict(X_te), pipe.predict_proba(X_te)[:, 1]
    # Guard against the failure that broke the first model: ignoring credit history.
    good, poor = X_te.copy(), X_te.copy()
    good["Credit_History"], poor["Credit_History"] = 1, 0
    credit_effect = float(pipe.predict_proba(good)[:, 1].mean() - pipe.predict_proba(poor)[:, 1].mean())

    metrics = {
        "model": best,
        "cv_roc_auc": cv_auc,
        "test": {
            "accuracy": accuracy_score(y_te, pred),
            "precision": precision_score(y_te, pred),
            "recall": recall_score(y_te, pred),
            "f1": f1_score(y_te, pred),
            "roc_auc": roc_auc_score(y_te, proba),
            "confusion_matrix": confusion_matrix(y_te, pred).tolist(),
        },
        "credit_history_effect": credit_effect,
        "rows": {"train": len(X_tr), "test": len(X_te)},
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipe, "features": ml.FEATURE_COLUMNS,
                 "sklearn_version": sklearn.__version__, "metrics": metrics}, out)
    out.with_suffix(".metrics.json").write_text(json.dumps(metrics, indent=2))

    print(json.dumps(metrics, indent=2))
    if credit_effect < 0.10:
        print("\nWARNING: the model barely reacts to Credit_History. Check the data before using it.")
    print(f"\nSaved {out}")
    return metrics


if __name__ == "__main__":
    main()

