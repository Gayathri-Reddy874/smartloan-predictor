import pytest

from app import create_app, inr, parse_application


@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True, "MODEL_PATH": str(tmp_path / "missing.joblib")})
    return app.test_client()


GOOD = {"dependents": "0", "education": "1", "employment": "0", "income": "60000",
        "co_app_income": "0", "loan_amount": "2000000", "loan_amount_term": "240", "history": "1"}


def test_inr_uses_indian_grouping():
    assert inr(1234567) == "₹12,34,567"
    assert inr(950) == "₹950"
    assert inr(100000) == "₹1,00,000"


def test_index_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Check your loan eligibility" in r.data


def test_valid_submission_returns_result(client):
    r = client.post("/predict", data=GOOD)
    assert r.status_code == 200
    assert b"Likely to be approved" in r.data
    assert "₹17,995".encode() in r.data or "₹17,996".encode() in r.data


def test_missing_fields_rerender_form_with_errors(client):
    r = client.post("/predict", data={})
    assert r.status_code == 400
    assert b"field-error" in r.data


def test_values_are_kept_after_error(client):
    r = client.post("/predict", data={**GOOD, "loan_amount_term": "9999"})
    assert r.status_code == 400
    assert b'value="60000"' in r.data


@pytest.mark.parametrize("field,value", [
    ("income", "abc"), ("income", "-5"), ("loan_amount", "nan"), ("loan_amount", "inf"),
    ("loan_amount_term", "0"), ("dependents", "9"), ("history", "2"),
])
def test_bad_values_rejected(field, value):
    applicant, errors, _ = parse_application({**GOOD, field: value})
    assert applicant is None and errors


def test_zero_total_income_rejected():
    _, errors, _ = parse_application({**GOOD, "income": "0", "co_app_income": "0"})
    assert "income" in errors


def test_get_predict_redirects(client):
    assert client.get("/predict").status_code == 302


def test_health(client):
    assert client.get("/health").get_json() == {"status": "ok", "model_loaded": False}


def test_security_headers(client):
    h = client.get("/").headers
    assert h["X-Frame-Options"] == "DENY"
    assert "script-src 'self'" in h["Content-Security-Policy"]


def test_unknown_page_is_404(client):
    assert client.get("/nope").status_code == 404


