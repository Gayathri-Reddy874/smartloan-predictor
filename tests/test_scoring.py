import pytest

from scoring import Applicant, affordable_principal, evaluate, monthly_emi


def applicant(**kw):
    base = dict(dependents=0, education=1, self_employed=0, applicant_income=60000,
                coapplicant_income=0, loan_amount=2_000_000, term_months=240, credit_history=1)
    base.update(kw)
    return Applicant(**base)


def test_emi_matches_known_value():
    # 20 lakh at 9% for 20 years is about 17,995 a month
    assert monthly_emi(2_000_000, 9, 240) == pytest.approx(17995, abs=2)


def test_emi_zero_interest():
    assert monthly_emi(120_000, 0, 12) == pytest.approx(10_000)


def test_affordable_principal_round_trips():
    p = affordable_principal(20_000, 9, 240)
    assert monthly_emi(p, 9, 240) == pytest.approx(20_000, rel=1e-6)


def test_strong_application_is_approved():
    r = evaluate(applicant(), 9)
    assert r.decision == "approved"
    assert r.score == sum(f.points for f in r.factors)
    assert sum(f.max_points for f in r.factors) == 100


def test_no_credit_history_never_auto_approved():
    r = evaluate(applicant(credit_history=0), 9)
    assert r.decision in {"review", "declined"}
    assert r.decision != "approved"


def test_emi_over_half_of_income_cannot_be_approved():
    r = evaluate(applicant(applicant_income=30000, loan_amount=2_500_000), 9)
    assert r.foir > 0.5
    assert r.decision != "approved"


def test_emi_over_sixty_percent_is_declined():
    r = evaluate(applicant(applicant_income=20000, loan_amount=2_500_000), 9)
    assert r.foir > 0.6
    assert r.decision == "declined"
    assert any("60%" in n for n in r.notes)


def test_unused_attributes_do_not_exist_on_applicant():
    # fairness guard: gender, marital status and property area are not inputs
    fields = set(Applicant.__dataclass_fields__)
    assert not fields & {"gender", "married", "marital_status", "property_area"}


def test_tips_suggest_affordable_loan_when_stretched():
    r = evaluate(applicant(applicant_income=30000), 9)
    assert any("keeps the EMI at 40%" in t for t in r.tips)


def test_higher_credit_never_lowers_score():
    assert evaluate(applicant(credit_history=1), 9).score > evaluate(applicant(credit_history=0), 9).score


