"""Explainable loan scorecard.

The decision is a transparent 100-point scorecard rather than a black box, so
every result can be explained to the applicant factor by factor.

Protected or proxy attributes (gender, marital status, property area) are
deliberately NOT used.
"""
from __future__ import annotations

from dataclasses import dataclass, field

APPROVE_AT = 70          # score needed for "approved"
REVIEW_AT = 50           # score needed for "review"
TARGET_FOIR = 0.40       # EMI share of income lenders are comfortable with
MAX_FOIR_FOR_APPROVAL = 0.50
HARD_DECLINE_FOIR = 0.60

_RANK = {"declined": 0, "review": 1, "approved": 2}


@dataclass(frozen=True)
class Applicant:
    dependents: int          # 0-3 (3 means 3 or more)
    education: int           # 1 = graduate, 0 = not graduate
    self_employed: int       # 1 = self-employed, 0 = salaried
    applicant_income: float  # monthly
    coapplicant_income: float  # monthly
    loan_amount: float
    term_months: int
    credit_history: int      # 1 = good history, 0 = none / poor

    @property
    def total_income(self) -> float:
        return self.applicant_income + self.coapplicant_income


@dataclass
class Factor:
    name: str
    detail: str
    points: int
    max_points: int
    status: str  # "strong" | "fair" | "weak"


@dataclass
class Assessment:
    decision: str                      # approved | review | declined
    score: int
    emi: float
    foir: float                        # EMI / total monthly income
    factors: list[Factor] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    tips: list[str] = field(default_factory=list)


def monthly_emi(principal: float, annual_rate_pct: float, months: int) -> float:
    """Standard reducing-balance EMI."""
    r = annual_rate_pct / 1200
    if r == 0:
        return principal / months
    growth = (1 + r) ** months
    return principal * r * growth / (growth - 1)


def affordable_principal(monthly_budget: float, annual_rate_pct: float, months: int) -> float:
    """Largest loan whose EMI fits inside `monthly_budget`."""
    r = annual_rate_pct / 1200
    if r == 0:
        return monthly_budget * months
    growth = (1 + r) ** months
    return monthly_budget * (growth - 1) / (r * growth)


def _inr(value: float) -> str:
    n = int(round(value))
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


def evaluate(a: Applicant, annual_rate_pct: float) -> Assessment:
    emi = monthly_emi(a.loan_amount, annual_rate_pct, a.term_months)
    foir = emi / a.total_income
    factors: list[Factor] = []

    # 1. Credit history (35)
    good = a.credit_history == 1
    factors.append(Factor(
        "Credit history",
        "Good repayment record" if good else "No usable credit history",
        35 if good else 0, 35, "strong" if good else "weak"))

    # 2. Affordability (35)
    for limit, pts in ((0.30, 35), (0.40, 28), (0.50, 18), (0.60, 8)):
        if foir <= limit:
            aff = pts
            break
    else:
        aff = 0
    factors.append(Factor(
        "Affordability",
        f"EMI of {_inr(emi)} is {foir:.0%} of monthly income",
        aff, 35, "strong" if aff >= 28 else "fair" if aff >= 18 else "weak"))

    # 3. Employment (10)
    emp = 6 if a.self_employed else 10
    factors.append(Factor(
        "Employment",
        "Self-employed" if a.self_employed else "Salaried",
        emp, 10, "fair" if a.self_employed else "strong"))

    # 4. Dependents (8)
    dep = {0: 8, 1: 6, 2: 4}.get(a.dependents, 2)
    factors.append(Factor(
        "Dependents",
        "None" if a.dependents == 0 else ("3 or more" if a.dependents >= 3 else str(a.dependents)),
        dep, 8, "strong" if dep >= 6 else "fair"))

    # 5. Education (6)
    edu = 6 if a.education else 3
    factors.append(Factor(
        "Education", "Graduate" if a.education else "Not a graduate",
        edu, 6, "strong" if a.education else "fair"))

    # 6. Second income (6)
    co = 6 if a.coapplicant_income > 0 else 0
    factors.append(Factor(
        "Second income",
        f"Co-applicant adds {_inr(a.coapplicant_income)} a month" if co else "No co-applicant income",
        co, 6, "strong" if co else "fair"))

    score = sum(f.points for f in factors)
    decision = "approved" if score >= APPROVE_AT else "review" if score >= REVIEW_AT else "declined"

    notes: list[str] = []

    def cap(to: str, why: str) -> None:
        nonlocal decision
        if _RANK[to] < _RANK[decision]:
            decision = to
            notes.append(why)

    if not good:
        cap("review", "Without a credit history, an application can't be approved automatically.")
    if foir > MAX_FOIR_FOR_APPROVAL:
        cap("review", "The EMI takes more than half of monthly income, which needs a manual look.")
    if foir > HARD_DECLINE_FOIR:
        cap("declined", "The EMI takes more than 60% of monthly income, above what lenders accept.")

    tips: list[str] = []
    if not good:
        tips.append("Build a repayment record first, for example a small loan or credit card paid on time, then apply again.")
    if foir > TARGET_FOIR:
        fit = affordable_principal(a.total_income * TARGET_FOIR, annual_rate_pct, a.term_months)
        tips.append(f"At {annual_rate_pct:g}% over {a.term_months} months, a loan of about {_inr(fit)} keeps the EMI at 40% of income.")
        if a.coapplicant_income == 0:
            tips.append("Adding a co-applicant with their own income lowers the EMI share and improves the score.")
        if a.term_months < 360:
            tips.append("A longer term lowers the monthly EMI, though you pay more interest overall.")

    return Assessment(decision, score, emi, foir, factors, notes, tips)


