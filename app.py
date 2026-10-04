"""SmartLoan Predictor: Flask web app.

Run locally:   flask --app app run --debug
Production:    gunicorn app:app
"""
from __future__ import annotations

import logging
import math
import os
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for

import ml
from scoring import Applicant, evaluate

BASE_DIR = Path(__file__).resolve().parent

DEPENDENT_CHOICES = {"0", "1", "2", "3"}
BINARY_CHOICES = {"0", "1"}


def inr(value) -> str:
    """Format a number as rupees with Indian digit grouping (₹12,34,567)."""
    n = int(round(float(value)))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return f"{'-' if n < 0 else ''}₹{s}"


def _number(form, name, label, lo, hi, errors):
    raw = (form.get(name) or "").strip().replace(",", "")
    if raw == "":
        errors[name] = f"Enter {label}."
        return None
    try:
        value = float(raw)
    except ValueError:
        errors[name] = f"{label.capitalize()} must be a number."
        return None
    if not math.isfinite(value) or not lo <= value <= hi:
        errors[name] = f"{label.capitalize()} must be between {lo:,} and {hi:,}."
        return None
    return value


def _choice(form, name, label, allowed, errors):
    raw = (form.get(name) or "").strip()
    if raw not in allowed:
        errors[name] = f"Select {label}."
        return None
    return int(raw)


def parse_application(form):
    """Validate the form. Returns (Applicant | None, errors, values)."""
    errors: dict[str, str] = {}
    values = {k: (form.get(k) or "").strip() for k in (
        "dependents", "education", "employment", "income", "co_app_income",
        "loan_amount", "loan_amount_term", "history")}

    dependents = _choice(form, "dependents", "the number of dependents", DEPENDENT_CHOICES, errors)
    education = _choice(form, "education", "an education level", BINARY_CHOICES, errors)
    employment = _choice(form, "employment", "an employment type", BINARY_CHOICES, errors)
    history = _choice(form, "history", "a credit history option", BINARY_CHOICES, errors)
    income = _number(form, "income", "monthly income", 0, 10_000_000, errors)
    co_income = _number(form, "co_app_income", "co-applicant income (0 if none)", 0, 10_000_000, errors)
    loan = _number(form, "loan_amount", "a loan amount", 10_000, 100_000_000, errors)
    term = _number(form, "loan_amount_term", "a loan term in months", 6, 480, errors)

    if income is not None and co_income is not None and income + co_income <= 0:
        errors["income"] = "Enter an income greater than zero."

    if errors:
        return None, errors, values
    return Applicant(dependents, education, employment, income, co_income,
                     loan, int(term), history), errors, values


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        ANNUAL_INTEREST_RATE=float(os.environ.get("ANNUAL_INTEREST_RATE", "9.0")),
        MODEL_PATH=os.environ.get("MODEL_PATH", str(BASE_DIR / "models" / "loan_model.joblib")),
    )
    if test_config:
        app.config.update(test_config)

    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app.jinja_env.filters["inr"] = inr
    app.extensions["ml_bundle"] = ml.load_model(app.config["MODEL_PATH"])
    app.logger.info("Statistical model %s", "loaded" if app.extensions["ml_bundle"] else "not found (scorecard only)")

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        resp.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
            "img-src 'self' data:; frame-ancestors 'none'")
        return resp

    @app.get("/")
    def index():
        return render_template("index.html", values={}, errors={}, rate=app.config["ANNUAL_INTEREST_RATE"])

    @app.post("/predict")
    def predict():
        rate = app.config["ANNUAL_INTEREST_RATE"]
        applicant, errors, values = parse_application(request.form)
        if errors:
            return render_template("index.html", values=values, errors=errors, rate=rate), 400

        assessment = evaluate(applicant, rate)
        probability = ml.approval_probability(app.extensions["ml_bundle"], applicant)
        app.logger.info("assessment decision=%s score=%d foir=%.2f", assessment.decision,
                        assessment.score, assessment.foir)  # no personal data is logged
        return render_template("result.html", a=assessment, applicant=applicant,
                               rate=rate, probability=probability)

    @app.get("/predict")
    def predict_get():
        return redirect(url_for("index"))

    @app.get("/health")
    def health():
        return jsonify(status="ok", model_loaded=app.extensions["ml_bundle"] is not None)

    @app.errorhandler(404)
    def not_found(_):
        return render_template("error.html", title="Page not found",
                               message="That page doesn't exist."), 404

    @app.errorhandler(500)
    def server_error(_):
        return render_template("error.html", title="Something went wrong",
                               message="The assessment couldn't be completed. Try again in a moment."), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
