import numpy as np
import pandas as pd

import ml
import train_model
from app import create_app
from scoring import Applicant


def synthetic_csv(path, n=500, seed=0):
    rng = np.random.default_rng(seed)
    credit = rng.integers(0, 2, n)
    income = rng.integers(2000, 15000, n)
    loan = rng.integers(50, 400, n)
    approved = (credit == 1) & (loan / income * 100 < 4) | (rng.random(n) < 0.05)
    pd.DataFrame({
        "Dependents": rng.choice(["0", "1", "2", "3+"], n),
        "Education": rng.choice(["Graduate", "Not Graduate"], n),
        "Self_Employed": rng.choice(["Yes", "No"], n),
        "ApplicantIncome": income, "CoapplicantIncome": rng.integers(0, 5000, n),
        "LoanAmount": loan, "Loan_Amount_Term": 360.0, "Credit_History": credit,
        "Loan_Status": np.where(approved, "Y", "N"),
    }).to_csv(path, index=False)


def test_training_script_produces_usable_model(tmp_path):
    data, out = tmp_path / "train.csv", tmp_path / "m.joblib"
    synthetic_csv(data)
    metrics = train_model.main(["--data", str(data), "--out", str(out)])
    assert out.exists() and out.with_suffix(".metrics.json").exists()
    assert metrics["credit_history_effect"] > 0.1

    bundle = ml.load_model(out)
    a = Applicant(0, 1, 0, 6000, 0, 150_000, 360, 1)
    b = Applicant(0, 1, 0, 6000, 0, 150_000, 360, 0)
    assert ml.approval_probability(bundle, a) > ml.approval_probability(bundle, b)

    app = create_app({"TESTING": True, "MODEL_PATH": str(out)})
    assert app.test_client().get("/health").get_json()["model_loaded"] is True


def test_missing_columns_give_clear_error():
    try:
        ml.prepare_training_frame(pd.DataFrame({"x": [1]}))
    except ValueError as e:
        assert "missing columns" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_corrupt_model_file_is_ignored(tmp_path):
    bad = tmp_path / "bad.joblib"
    bad.write_text("not a model")
    assert ml.load_model(bad) is None
