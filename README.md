# SmartLoan Predictor

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Flask](https://img.shields.io/badge/flask-3.1-lightgrey)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.8-orange)
![Tests](https://img.shields.io/badge/tests-30%20passing-brightgreen)

A Flask web app that tells a loan applicant how likely their application is to be approved, **and why**. It scores each application on a transparent 100-point scorecard, shows the points behind every factor, and suggests what would change the result.

## Screenshots

Add your own after running the app, saved in a `docs/` folder:

| Application form | Result |
|---|---|
| ![Form](docs/form.png) | ![Result](docs/result.png) |

## Features

- **Explainable decision.** Six factors with visible points, instead of an unexplained yes or no.
- **Live repayment preview.** The EMI and its share of income update as you type, using the same formula as the backend.
- **Actionable feedback.** Weak applications get specific advice, such as the loan size that would keep the EMI at 40% of income.
- **Input validation.** Bad or missing values re-open the form with clear messages and keep what you typed.
- **Fairness by design.** Gender, marital status and property location are not used in the decision.
- **Optional ML signal.** If you train a model with `train_model.py`, its approval probability is shown as a second opinion.
- **Production basics.** Application factory, `/health` endpoint, security headers (CSP, frame and content-type protection), gunicorn, Dockerfile, no personal data in logs, 30 automated tests.

## How the decision works

| Factor | Max points | Rule |
|---|---|---|
| Credit history | 35 | 35 for a good record, 0 otherwise |
| Affordability | 35 | EMI as a share of monthly income: ≤30% = 35, ≤40% = 28, ≤50% = 18, ≤60% = 8, above = 0 |
| Employment | 10 | Salaried 10, self-employed 6 |
| Dependents | 8 | 0 = 8, 1 = 6, 2 = 4, 3 or more = 2 |
| Education | 6 | Graduate 6, otherwise 3 |
| Second income | 6 | 6 if a co-applicant has income |

**Score 70 or more → approved. 50–69 → manual review. Below 50 → declined.**

Hard limits apply on top of the score:

- No credit history can never be approved automatically (maximum: review).
- EMI above 50% of income can never be approved (maximum: review).
- EMI above 60% of income is always declined.

The EMI uses the standard reducing-balance formula at an assumed annual rate (default 9%, set with `ANNUAL_INTEREST_RATE`).

## Project structure

```
smartloan-predictor/
├── app.py              # Flask app factory, validation, routes
├── scoring.py          # Scorecard, EMI maths, improvement tips
├── ml.py               # Optional model: features, loading, prediction
├── train_model.py      # Train and evaluate the optional model
├── templates/          # base, index (form), result, error
├── static/             # css/style.css, js/app.js (live EMI preview)
├── tests/              # scoring, app and training tests
├── models/  data/      # trained model and dataset (git-ignored)
├── requirements.txt    # pinned runtime dependencies
├── requirements-dev.txt
└── Dockerfile
```

## Quick start

Requires Python 3.11 or newer.

```bash
git clone https://github.com/Gayathri-Reddy874/smartloan-predictor.git
cd smartloan-predictor

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

flask --app app run --debug      # http://127.0.0.1:5000
```

### Run with Docker

```bash
docker build -t smartloan-predictor .
docker run -p 8000:8000 smartloan-predictor      # http://localhost:8000
```

### Run in production

```bash
gunicorn --bind 0.0.0.0:8000 --workers 2 app:app
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `ANNUAL_INTEREST_RATE` | `9.0` | Rate (% a year) used for EMI and affordability |
| `MODEL_PATH` | `models/loan_model.joblib` | Where to look for the optional model |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `FLASK_DEBUG` | unset | Set to `1` to enable debug mode when running `python app.py` |

## Optional: train the statistical model

1. Download the public *Loan Prediction* dataset (with a `Loan_Status` column of `Y`/`N`) and save it as `data/train.csv`.
2. Train:

   ```bash
   python train_model.py --data data/train.csv
   ```

3. Restart the app. The result page now shows the model's approval likelihood next to the scorecard.

The script compares logistic regression and a random forest with 5-fold cross-validation, keeps the better one, reports accuracy, precision, recall, F1, ROC-AUC and the confusion matrix on a held-out 20%, and saves `models/loan_model.joblib` plus `models/loan_model.metrics.json`. It also checks that the model actually reacts to credit history and warns if it does not. A model trained with a different scikit-learn version is ignored with a warning, so retrain after upgrading.

Put the real metrics from your run in this README once you have them.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Limitations and responsible use

- This is a demonstration project. It is **not** a credit decision and must not be used to approve or refuse real loans.
- The scorecard weights are hand-set for transparency, not fitted to lender outcomes.
- Income is treated as monthly and in rupees. The interest rate is a single assumption rather than a product rate.
- The training dataset is small, so any model trained on it should be treated as indicative.

## Roadmap

- Add a screenshot or short GIF of the form and result pages to `docs/`
- Fit scorecard weights from data and compare with the model
- SHAP explanations for the statistical model
- GitHub Actions workflow to run the tests on every push

## Author

**Mallareddygari Gayathri**
B.E. in AI/ML Engineering, Bengaluru, India

Data Science intern turned job-seeker, aiming for Data Analyst roles and growing toward Data Scientist and AI/ML Engineer work. This project came from finding that a first loan-approval model approved every applicant, then replacing it with a scorecard that explains each decision and a retraining script that checks the model actually uses credit history.

- GitHub: [@Gayathri-Reddy874](https://github.com/Gayathri-Reddy874)
- LinkedIn: add your profile link here
- Email: add your email here

If you find this useful, a star on the repo is appreciated.
