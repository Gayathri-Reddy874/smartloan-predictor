"""Optional statistical model (secondary signal).

The scorecard in scoring.py makes the decision. If a model trained with
train_model.py is present, the app also shows its approval probability.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

# No gender, marital status or property area on purpose.
FEATURE_COLUMNS = [
    "Dependents", "Education", "Self_Employed", "ApplicantIncome",
    "CoapplicantIncome", "LoanAmount", "Loan_Amount_Term", "Credit_History",
]
REQUIRED_RAW_COLUMNS = FEATURE_COLUMNS + ["Loan_Status"]


def prepare_training_frame(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Turn the Loan Prediction CSV into numeric features and a 0/1 target."""
    missing = [c for c in REQUIRED_RAW_COLUMNS if c not in raw.columns]
    if missing:
        raise ValueError(f"Dataset is missing columns: {', '.join(missing)}")
    df = raw.copy()
    df["Dependents"] = pd.to_numeric(df["Dependents"].astype(str).str.replace("+", "", regex=False), errors="coerce")
    df["Education"] = df["Education"].map({"Graduate": 1, "Not Graduate": 0})
    df["Self_Employed"] = df["Self_Employed"].map({"Yes": 1, "No": 0})
    for col in ("ApplicantIncome", "CoapplicantIncome", "LoanAmount", "Loan_Amount_Term", "Credit_History"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    y = (df["Loan_Status"].astype(str).str.upper() == "Y").astype(int)
    return df[FEATURE_COLUMNS], y


def applicant_frame(a) -> pd.DataFrame:
    """One-row frame for an Applicant. The dataset stores LoanAmount in thousands."""
    return pd.DataFrame([{
        "Dependents": a.dependents,
        "Education": a.education,
        "Self_Employed": a.self_employed,
        "ApplicantIncome": a.applicant_income,
        "CoapplicantIncome": a.coapplicant_income,
        "LoanAmount": a.loan_amount / 1000,
        "Loan_Amount_Term": a.term_months,
        "Credit_History": a.credit_history,
    }], columns=FEATURE_COLUMNS)


def load_model(path: str | Path):
    path = Path(path)
    if not path.exists():
        return None
    try:
        import joblib
        import sklearn

        bundle = joblib.load(path)
        if bundle.get("sklearn_version") != sklearn.__version__:
            log.warning("Model trained with scikit-learn %s but %s is installed; ignoring it. Retrain with train_model.py.",
                        bundle.get("sklearn_version"), sklearn.__version__)
            return None
        return bundle
    except Exception:  # corrupt or incompatible file must never take the app down
        log.exception("Could not load model from %s", path)
        return None


def approval_probability(bundle, applicant) -> float | None:
    if bundle is None:
        return None
    try:
        return float(bundle["pipeline"].predict_proba(applicant_frame(applicant))[0][1])
    except Exception:
        log.exception("Model prediction failed")
        return None


